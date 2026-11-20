import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.errors import ApiError
from app.core.security import digest, lock_merchant
from app.db.commerce import Customer, CustomerToken, EmailOutbox, RetentionCampaign, Sale
from app.schemas.commerce import RetentionView
from app.services.business import owned
from app.services.mail import queue_email
from app.services.transactions import atomic, audit


def eligible_customers(db, actor, inactive_days):
    cutoff = datetime.now(UTC) - timedelta(days=inactive_days)
    latest = (
        select(Sale.customer_id.label("customer_id"), func.max(Sale.created_at).label("last_sale"))
        .where(
            Sale.merchant_id == actor.merchant_id,
            Sale.status == "RECORDED",
            Sale.customer_id.is_not(None),
        )
        .group_by(Sale.customer_id)
        .subquery()
    )
    return db.scalars(
        select(Customer)
        .join(latest, latest.c.customer_id == Customer.id)
        .where(
            Customer.merchant_id == actor.merchant_id,
            Customer.marketing_opt_in.is_(True),
            Customer.consent_at.is_not(None),
            Customer.email.is_not(None),
            latest.c.last_sale < cutoff,
        )
        .order_by(Customer.id)
        .limit(100)
    ).all()


@atomic
def create_retention(db, actor, payload):
    lock_merchant(db, actor)
    eligible = {row.id for row in eligible_customers(db, actor, payload.inactive_days)}
    if not set(payload.customer_ids) <= eligible or len(set(payload.customer_ids)) != len(
        payload.customer_ids
    ):
        raise ApiError(
            422,
            "INELIGIBLE_CUSTOMERS",
            "Select distinct, opted-in inactive customers from the preview",
        )
    row = RetentionCampaign(merchant_id=actor.merchant_id, **payload.model_dump(mode="json"))
    db.add(row)
    db.flush()
    audit(db, actor, "RETENTION_DRAFT_CREATED", row.id)
    return RetentionView.model_validate(row)


@atomic
def retention_action(db, actor, campaign_id, action, settings):
    lock_merchant(db, actor)
    row = owned(db, RetentionCampaign, actor.merchant_id, campaign_id, lock=True)
    expected, target = ("DRAFT", "APPROVED") if action == "approve" else ("APPROVED", "QUEUED")
    if row.status == target:
        return RetentionView.model_validate(row)
    if row.status != expected:
        raise ApiError(409, "INVALID_STATE", "Retention campaign cannot perform this transition")
    if action == "queue":
        eligible = {
            customer.id: customer for customer in eligible_customers(db, actor, row.inactive_days)
        }
        cutoff = datetime.now(UTC) - timedelta(days=7)
        for customer_id in row.customer_ids:
            from uuid import UUID

            customer = eligible.get(UUID(customer_id))
            if customer is None:
                continue
            pending = db.scalar(
                select(EmailOutbox.id).where(
                    EmailOutbox.merchant_id == actor.merchant_id,
                    EmailOutbox.recipient == customer.email,
                    EmailOutbox.kind == "MARKETING",
                    EmailOutbox.created_at >= cutoff,
                    EmailOutbox.status.not_in(["FAILED", "SUPPRESSED"]),
                )
            )
            if pending or (customer.last_marketing_at and customer.last_marketing_at >= cutoff):
                continue
            raw = secrets.token_urlsafe(32)
            token = CustomerToken(
                merchant_id=actor.merchant_id,
                customer_id=customer.id,
                purpose="UNSUBSCRIBE",
                token_hash=digest(raw),
                expires_at=datetime.now(UTC) + timedelta(days=90),
            )
            db.add(token)
            body = (
                row.body + f"\n\nStop marketing messages:\n{settings.public_base_url.rstrip('/')}"
                f"/customer#flow=unsubscribe&token={raw}"
            )
            queue_email(
                db,
                settings,
                actor.merchant_id,
                customer.email,
                row.subject,
                body,
                "MARKETING",
                f"retention:{row.id}:{customer.id}",
                customer.id,
            )
            row.queued_count += 1
        # No external delivery occurs here. The worker rechecks consent and delivery configuration.
    row.status = target
    audit(db, actor, "RETENTION_" + target, row.id, {"queued_count": row.queued_count})
    db.flush()
    return RetentionView.model_validate(row)
