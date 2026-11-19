from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from .context import days_between, prepare, rounded_ratio
from .forecast import weekday_predictions


def evaluate_forecast(transactions, config, context=None) -> dict:
    data = prepare(transactions, config, context)
    complete = data.complete_days()
    result = {
        "status": "INSUFFICIENT_DATA",
        "method": "WEEKDAY_MEAN_BASELINE",
        "training_days": 0,
        "holdout_days": 0,
        "mae_paise": None,
        "flat_baseline_mae_paise": None,
        "holdout": [],
        "limitations": [],
    }
    if not complete:
        result["limitations"].append(
            "No complete historical days are available for evaluation."
        )
        return result
    # Seven consecutive calendar days, never seven disconnected observations.
    holdout = days_between(complete[-1] - timedelta(days=6), complete[-1])
    training = [day for day in complete if day < holdout[0]]
    result["training_days"] = len(training)
    if not set(holdout) <= set(complete):
        result["limitations"].append(
            "The final seven-day calendar holdout contains incomplete days."
        )
        return result
    predictions = weekday_predictions(data, training, holdout)
    if predictions is None:
        result["limitations"].append(
            "Training before the holdout requires 28 complete days and three observations per predicted weekday."
        )
        return result
    totals = data.successful_totals()
    flat = rounded_ratio(sum(totals[day] for day in training), len(training))
    error = sum(
        abs(totals[day] - prediction)
        for day, prediction in zip(holdout, predictions, strict=True)
    )
    flat_error = sum(abs(totals[day] - flat) for day in holdout)

    def mean(value):
        return float(
            (Decimal(value) / 7).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )

    result.update(
        status="AVAILABLE",
        holdout_days=7,
        mae_paise=mean(error),
        flat_baseline_mae_paise=mean(flat_error),
        holdout=[
            {
                "date": day.isoformat(),
                "actual_paise": totals[day],
                "predicted_paise": prediction,
            }
            for day, prediction in zip(holdout, predictions, strict=True)
        ],
    )
    result["limitations"] = [
        "Both baselines train only before the seven-day holdout; MAE is rounded to 0.01 paise.",
        "Current-status data may reflect later refunds; historical settlement snapshots are not reconstructed.",
        "Evaluation on test or simulated inputs is not evidence of real merchant forecast accuracy.",
    ]
    return result
