"""Provisional Python inputs from the Member 3 handoff.

These models validate structure, not payment authenticity or authorization.
Shared contract freeze with Member 2 is still required. No provider-specific
conversion, database connection, or synthetic transaction generation belongs here.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    model_validator,
)


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise ValueError(
            "identifier must be 1-100 letters, digits, underscores or hyphens"
        )
    return value


def _aware_timestamp(value: str) -> str:
    # Require an explicit offset. Never silently interpret a naive provider date
    # as UTC or as the merchant's timezone.
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)",
        value,
    ):
        raise ValueError("timestamp must be ISO 8601 with seconds and Z or an offset")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            "timestamp must be a valid timezone-aware date and time"
        ) from exc
    if parsed.utcoffset() is None:
        raise ValueError("timestamp requires an explicit timezone offset")
    # Preserve the supplied value. UTC normalization belongs to the ingestion
    # boundary, not an implicit mutation of an analytics input.
    return value


def _calendar_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("reporting date must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError("reporting date must be YYYY-MM-DD")
    return value


def _timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("timezone must be an available IANA timezone name") from exc
    return value


Identifier = Annotated[
    StrictStr,
    Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$"),
    AfterValidator(_identifier),
]
AwareTimestamp = Annotated[
    StrictStr,
    AfterValidator(_aware_timestamp),
    Field(
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$",
        json_schema_extra={"format": "date-time"},
    ),
]
CalendarDate = Annotated[
    StrictStr,
    AfterValidator(_calendar_date),
    Field(pattern=r"^\d{4}-\d{2}-\d{2}$", json_schema_extra={"format": "date"}),
]
TimezoneName = Annotated[StrictStr, AfterValidator(_timezone)]
TransactionStatus = Literal["SUCCESS", "PENDING", "FAILED", "REFUNDED"]


class _InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


class TransactionInput(_InputModel):
    """Canonical input from an authorized backend, not a raw provider CSV row.

    `amount_paise` is strict positive integer storage, capped at the backend's
    canonical maximum. Strings, floats and bools are not coerced. The package's
    batch boundary rejects duplicate IDs and mixed merchants.
    """

    merchant_id: Identifier
    transaction_id: Identifier
    amount_paise: Annotated[StrictInt, Field(gt=0, le=1_000_000_000_000)]
    timestamp: AwareTimestamp
    status: TransactionStatus


class AnalyticsConfig(_InputModel):
    """Local-calendar reporting bounds; completeness is not inferred from them.

    Start and end are inclusive merchant-local dates. Coverage, historical
    lookback and the calculation clock travel separately in AnalyticsContext.
    """

    start_date: CalendarDate
    end_date: CalendarDate
    timezone: TimezoneName = "Asia/Kolkata"

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        if self.start_date < "2000-01-01" or self.end_date > "2100-12-31":
            raise ValueError("Reporting dates must be within 2000-2100")
        return self
