"""Installable pure-Python analytics entry point consumed by the Member 2 adapter."""

from pydantic import BaseModel, ConfigDict, Field

from .context import AnalyticsContext
from .evaluation import evaluate_forecast
from .forecast import forecast_collections
from .metrics import calculate_metrics
from .recommendations import recommend_campaign
from .schemas import AnalyticsConfig, TransactionInput
from .summaries import generate_daily_summary
from .trends import analyze_trends


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transactions: list[TransactionInput] = Field(max_length=50000)
    config: AnalyticsConfig
    context: AnalyticsContext = Field(default_factory=AnalyticsContext)
    merchant_settings: dict = Field(default_factory=dict)


def run(operation: str, dataset: dict) -> dict:
    parsed = Dataset.model_validate(dataset)
    rows, config, context = parsed.transactions, parsed.config, parsed.context
    if operation == "dashboard":
        return calculate_metrics(rows, config, context)
    if operation == "analytics":
        return analyze_trends(rows, config, context)
    if operation == "forecast":
        return forecast_collections(rows, config, context, context.horizon_days)
    if operation == "evaluation":
        return evaluate_forecast(rows, config, context)
    if operation == "recommendation":
        return recommend_campaign(rows, config, parsed.merchant_settings, context)
    if operation == "summary":
        return generate_daily_summary(rows, config, context, context.locale)
    raise ValueError("Unsupported analytics operation")
