"""Developer 2's integration boundary. No analytics calculations live here."""

import importlib
import json
from datetime import UTC, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.errors import ApiError
from app.db.models import Coverage, Merchant, MerchantSettings, Transaction
from app.schemas.analytics import RESULT_MODELS


class AnalyticsProvider(Protocol):
    def run(self, operation: str, dataset: dict) -> dict: ...


class Member3AnalyticsProvider:
    """Validate with the supplied P3 package; discover its optional calculation entry point."""

    def __init__(self, *, require_calculations=False):
        self.schemas = importlib.import_module("bizbazaar_analytics.schemas")
        self.allow_calculations = require_calculations
        self.runner = None
        try:
            api = importlib.import_module("bizbazaar_analytics.api")
            candidate = getattr(api, "run", None)
            if callable(candidate):
                self.runner = candidate
        except ModuleNotFoundError as exc:
            if exc.name != "bizbazaar_analytics.api":
                raise
        if require_calculations and self.runner is None:
            raise RuntimeError(
                "Member 3 has supplied input validation, but not api.run calculations"
            )

    def validate_inputs(self, dataset):
        # P3 rejects extra fields. Context is a separate extension, never injected into its models.
        transactions = [
            self.schemas.TransactionInput.model_validate(row) for row in dataset["transactions"]
        ]
        config = self.schemas.AnalyticsConfig.model_validate(dataset["config"])
        return transactions, config

    def run(self, operation, dataset):
        transactions, config = self.validate_inputs(dataset)
        if self.runner is None or not self.allow_calculations:
            raise NotImplementedError("Analytics calculation execution is disabled")
        validated = dict(
            dataset,
            transactions=[row.model_dump(mode="json") for row in transactions],
            config=config.model_dump(mode="json"),
        )
        return self.runner(operation, validated)


# Backward compatible import name for the original startup integration.
RealAnalyticsProvider = Member3AnalyticsProvider


def require_json_result(result, operation):
    json.dumps(result, allow_nan=False)
    return RESULT_MODELS[operation].model_validate(result).model_dump(mode="json")


def build_dataset(db, actor, start_date, end_date, includes_simulated, max_days):
    if end_date < start_date or (end_date - start_date).days >= max_days:
        raise ApiError(422, "INVALID_RANGE", f"Select between 1 and {max_days} report days")
    merchant = db.get(Merchant, actor.merchant_id)
    tz = ZoneInfo(merchant.timezone)
    # Report windows and historical lookback are distinct. Keep both explicit for P3.
    history_start = start_date - timedelta(days=90)
    lower = datetime.combine(history_start, time.min, tzinfo=tz).astimezone(UTC)
    upper = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz).astimezone(UTC)
    query = select(Transaction).where(
        Transaction.merchant_id == actor.merchant_id,
        Transaction.timestamp >= lower,
        Transaction.timestamp < upper,
    )
    if not includes_simulated:
        query = query.where(Transaction.is_simulated.is_(False))
    # Bounded reads: refuse oversized reports rather than silently truncating financial data.
    rows = db.scalars(query.order_by(Transaction.timestamp, Transaction.id).limit(50001)).all()
    if len(rows) > 50000:
        raise ApiError(422, "REPORT_TOO_LARGE", "Select a smaller report period")
    coverage = db.scalars(
        select(Coverage)
        .where(
            Coverage.merchant_id == actor.merchant_id,
            Coverage.date >= history_start,
            Coverage.date <= end_date,
            Coverage.includes_simulated == includes_simulated,
        )
        .order_by(Coverage.date)
    ).all()
    settings = db.get(MerchantSettings, actor.merchant_id)
    return {
        "transactions": [
            {
                "merchant_id": str(row.merchant_id),
                "transaction_id": row.transaction_id,
                "amount_paise": row.amount_paise,
                "timestamp": row.timestamp.isoformat(),
                "status": row.status,
            }
            for row in rows
        ],
        "config": {
            "timezone": merchant.timezone,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "context": {
            "as_of_timestamp": datetime.now(UTC).isoformat(),
            "history_start_date": history_start.isoformat(),
            "includes_simulated": includes_simulated,
            "coverage": [
                {"date": row.date.isoformat(), "status": row.status, "provenance": row.provenance}
                for row in coverage
            ],
        },
        "merchant_settings": settings.promotion if settings else {},
    }


def analytics_response(
    db,
    actor,
    provider,
    operation,
    start_date,
    end_date,
    includes_simulated,
    max_days,
    horizon_days=7,
    locale="en-IN",
    decline_threshold_percent=10,
):
    # One repeatable-read snapshot for transactions, coverage, settings, and dashboard campaigns.
    # Authentication used this request's session already; begin a fresh read-only snapshot.
    db.rollback()
    from sqlalchemy import text

    db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    dataset = build_dataset(db, actor, start_date, end_date, includes_simulated, max_days)
    # Inputs are materialized; release the DB connection before optional model/network work.
    db.rollback()
    dataset["context"]["horizon_days"] = horizon_days
    dataset["context"]["locale"] = locale
    dataset["context"]["decline_threshold_percent"] = decline_threshold_percent
    result = None
    limitations = ["Recorded activity is not necessarily total shop sales or profit."]
    if provider is not None:
        try:
            result = require_json_result(provider.run(operation, dataset), operation)
        except NotImplementedError:
            limitations.append("Analytics calculations are disabled in foundation mode.")
        except Exception:
            raise ApiError(
                503, "ANALYTICS_UNAVAILABLE", "Analytics provider could not return a valid result"
            ) from None
    else:
        limitations.append(
            "No analytics provider is configured; no calculated results are returned."
        )
    return {
        "status": "AVAILABLE" if result is not None else "UNAVAILABLE",
        "generation_mode": "REAL" if result is not None else "UNAVAILABLE",
        "start_date": start_date,
        "end_date": end_date,
        "timezone": dataset["config"]["timezone"],
        "includes_simulated": includes_simulated,
        "result": result,
        "limitations": limitations,
    }
