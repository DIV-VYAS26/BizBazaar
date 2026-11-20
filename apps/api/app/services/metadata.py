from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.errors import ApiError
from app.core.security import lock_merchant
from app.db.models import Coverage, Merchant, MerchantSettings
from app.schemas.analytics import CoverageDeclaration, PromotionSettings
from app.services.transactions import atomic, audit


@atomic
def declare_coverage(db, actor, payload):
    merchant = lock_merchant(db, actor)
    today = datetime.now(UTC).astimezone(ZoneInfo(merchant.timezone)).date()
    for item in payload.items:
        if item.date > today or (item.status == "COMPLETE" and item.date == today):
            raise ApiError(422, "INVALID_COVERAGE", "Only past days can be declared complete")
        row = db.scalar(
            select(Coverage).where(
                Coverage.merchant_id == actor.merchant_id,
                Coverage.date == item.date,
                Coverage.includes_simulated == item.includes_simulated,
            )
        )
        if row:
            row.status, row.provenance = item.status, item.provenance
        else:
            db.add(Coverage(merchant_id=actor.merchant_id, **item.model_dump()))
        audit(db, actor, "COVERAGE_DECLARED", item.date.isoformat(), item.model_dump(mode="json"))
    db.flush()
    return payload


def invalidate_coverage(db, actor, timestamp, is_simulated):
    merchant = db.get(Merchant, actor.merchant_id)
    local_date = timestamp.astimezone(ZoneInfo(merchant.timezone)).date()
    query = select(Coverage).where(
        Coverage.merchant_id == actor.merchant_id,
        Coverage.date == local_date,
        Coverage.status == "COMPLETE",
    )
    if is_simulated:
        query = query.where(Coverage.includes_simulated.is_(True))
    for row in db.scalars(query).all():
        row.status = "PARTIAL"
        row.provenance = "Activity changed after completeness declaration; revalidation required"
        audit(
            db,
            actor,
            "COVERAGE_INVALIDATED",
            row.date.isoformat(),
            {"includes_simulated": row.includes_simulated},
        )


@atomic
def update_settings(db, actor, payload):
    lock_merchant(db, actor)
    row = db.get(MerchantSettings, actor.merchant_id)
    if row:
        row.promotion = payload.model_dump(mode="json")
    else:
        db.add(
            MerchantSettings(
                merchant_id=actor.merchant_id, promotion=payload.model_dump(mode="json")
            )
        )
    audit(
        db, actor, "PROMOTION_SETTINGS_UPDATED", actor.merchant_id, payload.model_dump(mode="json")
    )
    return payload


def read_settings(db, actor):
    row = db.get(MerchantSettings, actor.merchant_id)
    return PromotionSettings.model_validate(row.promotion) if row else None


def read_coverage(db, actor, start_date, end_date, includes_simulated):
    if end_date < start_date or (end_date - start_date).days >= 366:
        raise ApiError(422, "INVALID_RANGE", "Select between 1 and 366 coverage days")
    rows = db.scalars(
        select(Coverage)
        .where(
            Coverage.merchant_id == actor.merchant_id,
            Coverage.date >= start_date,
            Coverage.date <= end_date,
            Coverage.includes_simulated == includes_simulated,
        )
        .order_by(Coverage.date)
    ).all()
    return [CoverageDeclaration.model_validate(row) for row in rows]
