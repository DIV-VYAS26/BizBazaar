"""Pure, validated reporting context. No database or web framework dependency."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from .schemas import AnalyticsConfig, AwareTimestamp, CalendarDate, TransactionInput


class ObservedDay(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    date: CalendarDate
    status: Literal["COMPLETE", "PARTIAL", "UNKNOWN"]
    provenance: str = Field(min_length=1, max_length=200)


class AnalyticsContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    history_start_date: CalendarDate | None = None
    includes_simulated: StrictBool = True
    coverage: list[ObservedDay] = Field(default_factory=list, max_length=500)
    horizon_days: int = Field(default=7, strict=True, ge=1, le=14)
    decline_threshold_percent: int = Field(default=10, strict=True, ge=1, le=100)
    as_of_timestamp: AwareTimestamp | None = None
    locale: Literal["en-IN", "hi-IN"] = "en-IN"


def rounded_ratio(total: int, count: int) -> int:
    if count <= 0:
        raise ValueError("A positive denominator is required")
    # Exact positive half-up division; binary floats never enter money calculations.
    return (2 * total + count) // (2 * count)


def money_text(paise: int) -> str:
    return f"₹{paise // 100:,}.{paise % 100:02d}"


def days_between(start: date, end: date):
    return [
        start + timedelta(days=offset)
        for offset in range(max(0, (end - start).days + 1))
    ]


@dataclass
class PreparedData:
    config: AnalyticsConfig
    context: AnalyticsContext
    rows: list[tuple[TransactionInput, date]]
    coverage: dict[date, str]
    now: datetime

    @property
    def start(self):
        return date.fromisoformat(self.config.start_date)

    @property
    def end(self):
        return date.fromisoformat(self.config.end_date)

    @property
    def today(self):
        return self.now.astimezone(ZoneInfo(self.config.timezone)).date()

    def complete_days(self, through=None):
        through = min(through or self.end, self.end, self.today - timedelta(days=1))
        history = (
            date.fromisoformat(self.context.history_start_date)
            if self.context.history_start_date
            else self.start
        )
        return sorted(
            day
            for day, status in self.coverage.items()
            if status == "COMPLETE" and history <= day <= through
        )

    def successful_totals(self):
        totals = defaultdict(int)
        for row, day in self.rows:
            if row.status == "SUCCESS":
                totals[day] += row.amount_paise
        return totals


def prepare(transactions, config, context=None) -> PreparedData:
    config = (
        config
        if isinstance(config, AnalyticsConfig)
        else AnalyticsConfig.model_validate(config)
    )
    context = (
        context
        if isinstance(context, AnalyticsContext)
        else AnalyticsContext.model_validate(context or {})
    )
    start, end = (
        date.fromisoformat(config.start_date),
        date.fromisoformat(config.end_date),
    )
    if (end - start).days >= 366:
        raise ValueError("Reporting range must not exceed 366 days")
    history = (
        date.fromisoformat(context.history_start_date)
        if context.history_start_date
        else start
    )
    if history > start or (start - history).days > 90:
        raise ValueError(
            "History must start within 90 days before the reporting window"
        )
    now = (
        datetime.fromisoformat(context.as_of_timestamp)
        if context.as_of_timestamp
        else datetime.now(UTC)
    )
    if now.utcoffset() is None:
        raise ValueError("as_of_timestamp must include its timezone")
    coverage = {}
    for item in context.coverage:
        day = date.fromisoformat(item.date)
        if day in coverage:
            raise ValueError("Duplicate coverage date")
        if not history <= day <= end:
            raise ValueError("Coverage falls outside the input history window")
        coverage[day] = item.status
    ids, merchants, rows = set(), set(), []
    for item in transactions:
        row = (
            item
            if isinstance(item, TransactionInput)
            else TransactionInput.model_validate(item)
        )
        key = (row.merchant_id, row.transaction_id)
        if key in ids:
            raise ValueError("Duplicate transaction input")
        ids.add(key)
        merchants.add(row.merchant_id)
        if len(merchants) > 1:
            raise ValueError("Analytics accepts one merchant at a time")
        local_day = (
            datetime.fromisoformat(row.timestamp)
            .astimezone(ZoneInfo(config.timezone))
            .date()
        )
        if not history <= local_day <= end:
            raise ValueError("Transaction falls outside the input history window")
        rows.append((row, local_day))
    return PreparedData(config, context, rows, coverage, now)


def decimal_percent(numerator: Decimal, denominator: Decimal) -> float:
    return float(
        (100 * numerator / denominator).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    )
