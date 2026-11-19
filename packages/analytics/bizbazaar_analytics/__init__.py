"""Pure merchant analytics: exact metrics, transparent baselines and grounded summaries."""

from .evaluation import evaluate_forecast
from .forecast import forecast_collections
from .metrics import calculate_metrics
from .recommendations import recommend_campaign
from .schemas import AnalyticsConfig, TransactionInput, TransactionStatus
from .summaries import generate_daily_summary
from .trends import analyze_trends

__all__ = [
    "AnalyticsConfig",
    "TransactionInput",
    "TransactionStatus",
    "analyze_trends",
    "calculate_metrics",
    "evaluate_forecast",
    "forecast_collections",
    "generate_daily_summary",
    "recommend_campaign",
]
