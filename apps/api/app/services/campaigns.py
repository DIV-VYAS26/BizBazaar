from datetime import UTC, datetime

from sqlalchemy import select

from app.core.errors import ApiError
from app.core.security import lock_merchant
from app.db.models import Campaign
from app.schemas.api import CampaignView
from app.services.transactions import atomic, audit


def now_utc():
    return datetime.now(UTC)


def owned_campaign(db, actor, campaign_id, *, lock=False):
    query = select(Campaign).where(
        Campaign.id == campaign_id, Campaign.merchant_id == actor.merchant_id
    )
    if lock:
        query = query.with_for_update()
    row = db.scalar(query.execution_options(populate_existing=True))
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Campaign not found")
    return row


def reconcile_expiry(db, actor, now):
    rows = db.scalars(
        select(Campaign)
        .where(Campaign.merchant_id == actor.merchant_id, Campaign.status == "ACTIVE")
        .with_for_update()
    ).all()
    for row in rows:
        if now >= row.ends_at:
            row.status = "COMPLETED"
            audit(db, actor, "CAMPAIGN_EXPIRED", row.id)
    db.flush()


@atomic
def create_campaign(db, actor, payload):
    lock_merchant(db, actor)
    if payload.ends_at <= now_utc():
        raise ApiError(422, "INVALID_DATES", "Campaign end must be in the future")
    row = Campaign(merchant_id=actor.merchant_id, **payload.model_dump(mode="json"))
    # ORM timestamp columns accept datetime values, not JSON strings.
    row.starts_at, row.ends_at = payload.starts_at, payload.ends_at
    db.add(row)
    db.flush()
    audit(db, actor, "CAMPAIGN_CREATED", row.id)
    return CampaignView.model_validate(row)


@atomic
def transition_campaign(db, actor, campaign_id, action):
    lock_merchant(db, actor)
    now = now_utc()
    reconcile_expiry(db, actor, now)
    row = owned_campaign(db, actor, campaign_id, lock=True)
    targets = {"approve": "APPROVED", "activate": "ACTIVE", "complete": "COMPLETED"}
    expected = {"approve": "DRAFT", "activate": "APPROVED", "complete": "ACTIVE"}
    if row.status == targets[action]:
        return CampaignView.model_validate(row)
    if row.status != expected[action]:
        raise ApiError(409, "INVALID_STATE", "Campaign cannot perform this transition")
    if action == "approve":
        if now >= row.ends_at:
            raise ApiError(409, "CAMPAIGN_EXPIRED", "Campaign has expired")
        row.approved_by, row.approved_at = actor.session_id, now
    if action == "activate":
        if not row.starts_at <= now < row.ends_at:
            raise ApiError(409, "OUTSIDE_WINDOW", "Campaign is outside its activation window")
        active = db.scalar(
            select(Campaign.id).where(
                Campaign.merchant_id == actor.merchant_id, Campaign.status == "ACTIVE"
            )
        )
        if active:
            raise ApiError(409, "ACTIVE_CAMPAIGN_EXISTS", "Complete the active campaign first")
    row.status = targets[action]
    audit(db, actor, f"CAMPAIGN_{targets[action]}", row.id)
    db.flush()
    return CampaignView.model_validate(row)
