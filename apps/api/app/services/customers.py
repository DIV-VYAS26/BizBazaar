import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.core.errors import ApiError
from app.core.security import digest, lock_merchant
from app.db.commerce import (
    CreditAccount,
    CreditAcknowledgement,
    CreditEvent,
    Customer,
    CustomerToken,
)
from app.schemas.commerce import CustomerView
from app.services.business import owned
from app.services.credit import ledger
from app.services.mail import queue_email
from app.services.transactions import atomic, audit, system_audit


def issue_customer_link(db, settings, customer, purpose):
    if not customer.email:
        raise ApiError(422, "EMAIL_REQUIRED", "Customer needs an email address for this link")
    raw = secrets.token_urlsafe(32)
    token = CustomerToken(
        merchant_id=customer.merchant_id,
        customer_id=customer.id,
        purpose=purpose,
        token_hash=digest(raw),
        expires_at=datetime.now(UTC) + timedelta(days=7 if purpose == "PORTAL" else 2),
    )
    db.add(token)
    db.flush()
    flow = "portal" if purpose == "PORTAL" else "consent"
    link = f"{settings.public_base_url.rstrip('/')}/customer#flow={flow}&token={raw}"
    subject = (
        "View your BizBazaar credit record"
        if purpose == "PORTAL"
        else "Confirm BizBazaar marketing preference"
    )
    queue_email(
        db,
        settings,
        customer.merchant_id,
        customer.email,
        subject,
        f"Open this private link to review and choose:\n{link}\nDo not share this link.",
        purpose,
        "customer-token:" + str(token.id),
        customer.id,
    )


@atomic
def create_customer(db, actor, payload, settings):
    lock_merchant(db, actor)
    row = Customer(merchant_id=actor.merchant_id, name=payload.name, email=payload.email)
    db.add(row)
    db.flush()
    if payload.request_marketing_consent:
        issue_customer_link(db, settings, row, "CONSENT")
    audit(db, actor, "CUSTOMER_CREATED", row.id)
    return CustomerView.model_validate(row)


@atomic
def update_customer(db, actor, customer_id, payload, settings):
    lock_merchant(db, actor)
    row = owned(db, Customer, actor.merchant_id, customer_id, lock=True)
    if row.email != payload.email:
        row.marketing_opt_in, row.consent_at = False, None
        db.execute(
            update(CustomerToken)
            .where(
                CustomerToken.merchant_id == actor.merchant_id,
                CustomerToken.customer_id == row.id,
                CustomerToken.consumed_at.is_(None),
            )
            .values(consumed_at=datetime.now(UTC))
        )
    row.name, row.email = payload.name, payload.email
    if payload.request_marketing_consent:
        issue_customer_link(db, settings, row, "CONSENT")
    audit(db, actor, "CUSTOMER_UPDATED", row.id)
    return CustomerView.model_validate(row)


@atomic
def customer_link(db, actor, customer_id, purpose, settings):
    lock_merchant(db, actor)
    row = owned(db, Customer, actor.merchant_id, customer_id)
    issue_customer_link(db, settings, row, purpose)
    audit(db, actor, "CUSTOMER_" + purpose + "_LINK_QUEUED", row.id)
    return {"message": "Private customer link queued"}


@atomic
def revoke_consent(db, actor, customer_id):
    lock_merchant(db, actor)
    row = owned(db, Customer, actor.merchant_id, customer_id, lock=True)
    row.marketing_opt_in, row.consent_at = False, None
    audit(db, actor, "CUSTOMER_MARKETING_REVOKED", row.id)
    return CustomerView.model_validate(row)


def token_customer(db, raw, purpose):
    row = db.scalar(
        select(CustomerToken)
        .where(CustomerToken.token_hash == digest(raw), CustomerToken.purpose == purpose)
        .execution_options(populate_existing=True)
    )
    if row is None or row.consumed_at or row.expires_at <= datetime.now(UTC):
        raise ApiError(401, "INVALID_CUSTOMER_LINK", "Customer link is invalid or expired")
    customer = owned(db, Customer, row.merchant_id, row.customer_id)
    return row, customer


def portal_view(db, raw):
    token, customer = token_customer(db, raw, "PORTAL")
    return ledger(db, token.merchant_id, customer.id)


def record_customer_decision(db, raw, payload):
    preview, _ = token_customer(db, raw, "PORTAL")
    from app.db.models import Merchant

    db.scalar(select(Merchant).where(Merchant.id == preview.merchant_id).with_for_update())
    token, customer = token_customer(db, raw, "PORTAL")
    event = owned(db, CreditEvent, token.merchant_id, payload.event_id)
    account = owned(db, CreditAccount, token.merchant_id, event.account_id)
    if account.customer_id != customer.id or event.kind != "CHARGE":
        raise ApiError(404, "NOT_FOUND", "Credit charge not found")
    if db.scalar(select(CreditEvent.id).where(CreditEvent.reverses_id == event.id)):
        raise ApiError(409, "REVERSED_CHARGE", "This charge has been reversed")
    previous = db.scalar(
        select(CreditAcknowledgement).where(CreditAcknowledgement.event_id == event.id)
    )
    if previous:
        if previous.decision != payload.decision or previous.note != payload.note:
            raise ApiError(409, "DECISION_EXISTS", "A customer decision is already recorded")
    else:
        db.add(
            CreditAcknowledgement(
                merchant_id=token.merchant_id,
                customer_id=customer.id,
                event_id=event.id,
                decision=payload.decision,
                note=payload.note,
            )
        )
        system_audit(
            db,
            token.merchant_id,
            "CUSTOMER_CREDIT_" + payload.decision,
            event.id,
            {"customer_id": str(customer.id)},
            actor_type="ACCOUNT_TOKEN",
        )
    db.commit()
    return ledger(db, token.merchant_id, customer.id)


def confirm_consent(db, raw, decision):
    purpose = "CONSENT" if decision == "OPT_IN" else "UNSUBSCRIBE"
    preview, _ = token_customer(db, raw, purpose)
    from app.db.models import Merchant

    db.scalar(select(Merchant).where(Merchant.id == preview.merchant_id).with_for_update())
    token, customer = token_customer(db, raw, purpose)
    token.consumed_at = datetime.now(UTC)
    customer.marketing_opt_in = decision == "OPT_IN"
    customer.consent_at = datetime.now(UTC) if customer.marketing_opt_in else None
    system_audit(
        db, token.merchant_id, "CUSTOMER_" + decision, customer.id, actor_type="ACCOUNT_TOKEN"
    )
    db.commit()
