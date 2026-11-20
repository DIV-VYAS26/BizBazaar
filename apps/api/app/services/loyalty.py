from sqlalchemy import func, select

from app.core.security import lock_merchant
from app.db.commerce import Customer, LoyaltyEvent, LoyaltyPolicy
from app.schemas.commerce import LoyaltyBalance, LoyaltyEventView, LoyaltySettings
from app.services.business import owned
from app.services.transactions import atomic, audit


def points_balance(db, merchant_id, customer_id):
    return int(
        db.scalar(
            select(func.coalesce(func.sum(LoyaltyEvent.points_delta), 0)).where(
                LoyaltyEvent.merchant_id == merchant_id, LoyaltyEvent.customer_id == customer_id
            )
        )
        or 0
    )


def get_loyalty(db, merchant_id, customer_id):
    owned(db, Customer, merchant_id, customer_id)
    points = points_balance(db, merchant_id, customer_id)
    rows = db.scalars(
        select(LoyaltyEvent)
        .where(LoyaltyEvent.merchant_id == merchant_id, LoyaltyEvent.customer_id == customer_id)
        .order_by(LoyaltyEvent.created_at.desc(), LoyaltyEvent.id)
        .limit(200)
    ).all()
    return LoyaltyBalance(
        balance_points=points,
        available_points=max(0, points),
        events=[LoyaltyEventView.model_validate(row) for row in rows],
    )


@atomic
def save_policy(db, actor, payload):
    lock_merchant(db, actor)
    row = db.get(LoyaltyPolicy, actor.merchant_id)
    if row is None:
        db.add(LoyaltyPolicy(merchant_id=actor.merchant_id, **payload.model_dump()))
    else:
        for key, value in payload.model_dump().items():
            setattr(row, key, value)
    audit(db, actor, "LOYALTY_POLICY_UPDATED", actor.merchant_id, payload.model_dump())
    return payload


def get_policy(db, actor):
    row = db.get(LoyaltyPolicy, actor.merchant_id)
    return LoyaltySettings.model_validate(row) if row else LoyaltySettings()
