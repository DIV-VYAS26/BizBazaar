"""Typed Developer 2 contracts; calculations remain owned by Developer 3."""

from datetime import date as CalendarDate
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.api import CampaignCreate, StrictModel

Count = Annotated[int, Field(strict=True, ge=0)]
Total = Annotated[int, Field(strict=True, ge=0)]


class CoverageDeclaration(StrictModel):
    date: CalendarDate = Field(ge=CalendarDate(2000, 1, 1), le=CalendarDate(2100, 12, 31))
    status: Literal["COMPLETE", "PARTIAL", "UNKNOWN"]
    provenance: str = Field(min_length=1, max_length=200, pattern=r"^[^\x00-\x1f\x7f]+$")
    includes_simulated: bool = Field(strict=True, default=True)


class CoverageBatch(StrictModel):
    items: list[CoverageDeclaration] = Field(min_length=1, max_length=366)

    @model_validator(mode="after")
    def distinct_dates(self):
        keys = [(item.date, item.includes_simulated) for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("Each date and simulation scope may be declared only once")
        return self


class PromotionSettings(StrictModel):
    type: Literal["NTH_PAYMENT", "COLLECTION_THRESHOLD"]
    rule_parameters: dict[str, int]
    reward_cost_paise: Annotated[int, Field(strict=True, gt=0, le=1_000_000_000_000)]
    budget_cap_paise: Annotated[int, Field(strict=True, gt=0, le=1_000_000_000_000)]
    duration_days: Annotated[int, Field(strict=True, ge=1, le=90)]

    @model_validator(mode="before")
    @classmethod
    def validate_campaign_rules(cls, values):
        if isinstance(values, dict):
            # Reuse the public campaign validator without creating a campaign or inventing terms.
            from datetime import UTC, datetime, timedelta

            start = datetime(2026, 1, 1, tzinfo=UTC)
            CampaignCreate.model_validate(
                {
                    "name": "Settings validation",
                    "starts_at": start,
                    "ends_at": start + timedelta(days=1),
                    **{key: value for key, value in values.items() if key != "duration_days"},
                }
            )
        return values


class DailyPoint(StrictModel):
    date: CalendarDate
    collections_paise: Total
    successful_count: Count


class WeekdayPoint(StrictModel):
    weekday: Annotated[int, Field(strict=True, ge=0, le=6)]
    collections_paise: Total
    observed_complete_days: Count


class StatusCounts(StrictModel):
    success: Count
    pending: Count
    failed: Count
    refunded: Count


class MetricsResult(StrictModel):
    collections_paise: Total
    successful_count: Count
    average_payment_paise: Total | None
    status_counts: StatusCounts
    daily_collections: list[DailyPoint]
    weekday_collections: list[WeekdayPoint]
    warnings: list[str]

    @model_validator(mode="after")
    def consistent_counts(self):
        if self.status_counts.success != self.successful_count:
            raise ValueError("Successful counts disagree")
        if (self.successful_count == 0) != (self.average_payment_paise is None):
            raise ValueError("Average must be null exactly when successful count is zero")
        return self


class SlowPeriod(StrictModel):
    weekday: Annotated[int, Field(strict=True, ge=0, le=6)]
    observed_complete_days: Count
    explanation: str


class TrendsResult(StrictModel):
    metrics: MetricsResult
    slow_periods: list[SlowPeriod]
    average_value_decline_percent: float | None = Field(allow_inf_nan=False)
    limitations: list[str]


class ForecastPoint(StrictModel):
    date: CalendarDate
    collections_paise: Total


class ForecastResult(StrictModel):
    status: Literal["AVAILABLE", "INSUFFICIENT_DATA"]
    method: Literal["WEEKDAY_MEAN_BASELINE"]
    history_days: Count
    forecast: list[ForecastPoint]
    projected_total_paise: Total | None
    limitations: list[str]

    @model_validator(mode="after")
    def insufficient_has_no_prediction(self):
        if self.status == "INSUFFICIENT_DATA" and self.forecast:
            raise ValueError("Insufficient history cannot contain predictions")
        if self.status == "INSUFFICIENT_DATA" and self.projected_total_paise is not None:
            raise ValueError("Insufficient history cannot contain a projected total")
        if self.status == "AVAILABLE" and (
            not self.forecast
            or self.projected_total_paise != sum(point.collections_paise for point in self.forecast)
        ):
            raise ValueError("Projected total must agree with available forecast points")
        return self


class HoldoutPoint(StrictModel):
    date: CalendarDate
    actual_paise: Total
    predicted_paise: Total


class ForecastEvaluationResult(StrictModel):
    status: Literal["AVAILABLE", "INSUFFICIENT_DATA"]
    method: Literal["WEEKDAY_MEAN_BASELINE"]
    training_days: Count
    holdout_days: Count
    mae_paise: float | None = Field(ge=0, allow_inf_nan=False)
    flat_baseline_mae_paise: float | None = Field(ge=0, allow_inf_nan=False)
    holdout: list[HoldoutPoint]
    limitations: list[str]

    @model_validator(mode="after")
    def complete_holdout(self):
        if self.status == "AVAILABLE" and (
            len(self.holdout) != 7
            or self.holdout_days != 7
            or self.training_days < 28
            or self.mae_paise is None
            or self.flat_baseline_mae_paise is None
        ):
            raise ValueError("Available evaluation requires a complete seven-day holdout")
        if self.status == "INSUFFICIENT_DATA" and (self.holdout or self.mae_paise is not None):
            raise ValueError("Insufficient evaluation cannot contain measured errors")
        return self


class RecommendationResult(StrictModel):
    suggested_action: CampaignCreate | None
    explanation: str
    source_metrics: MetricsResult
    data_sufficiency: Literal["SUFFICIENT", "INSUFFICIENT"]
    generation_mode: Literal["DETERMINISTIC_FALLBACK", "EXTERNAL_LLM"]
    limitations: list[str]


class SummaryResult(StrictModel):
    date: CalendarDate
    locale: Literal["en-IN", "hi-IN"]
    summary_text: str
    metrics: MetricsResult
    data_sufficiency: Literal["SUFFICIENT", "INSUFFICIENT"]
    generation_mode: Literal["DETERMINISTIC_FALLBACK", "EXTERNAL_LLM"]
    limitations: list[str]


class AnalyticsResponse[T](StrictModel):
    status: Literal["AVAILABLE", "UNAVAILABLE"]
    generation_mode: Literal["REAL", "UNAVAILABLE"]
    start_date: CalendarDate
    end_date: CalendarDate
    timezone: str
    includes_simulated: bool
    result: T | None
    limitations: list[str]

    @model_validator(mode="after")
    def consistent_availability(self):
        available = self.status == "AVAILABLE"
        if available != (self.result is not None) or available != (self.generation_mode == "REAL"):
            raise ValueError("Availability, mode and result must agree")
        return self


class DashboardEnvelope(AnalyticsResponse[MetricsResult]):
    pass


class TrendsEnvelope(AnalyticsResponse[TrendsResult]):
    pass


class ForecastEnvelope(AnalyticsResponse[ForecastResult]):
    pass


class RecommendationEnvelope(AnalyticsResponse[RecommendationResult]):
    pass


class SummaryEnvelope(AnalyticsResponse[SummaryResult]):
    pass


class EvaluationEnvelope(AnalyticsResponse[ForecastEvaluationResult]):
    pass


RESULT_MODELS = {
    "dashboard": MetricsResult,
    "analytics": TrendsResult,
    "forecast": ForecastResult,
    "recommendation": RecommendationResult,
    "summary": SummaryResult,
    "evaluation": ForecastEvaluationResult,
}
