from collections import defaultdict
from datetime import timedelta

from .context import prepare, rounded_ratio


def weekday_predictions(data, training_days, prediction_days):
    weekday_values = defaultdict(list)
    totals = data.successful_totals()
    for day in training_days:
        weekday_values[day.weekday()].append(totals[day])
    if len(training_days) < 28 or any(
        len(weekday_values[day.weekday()]) < 3 for day in prediction_days
    ):
        return None
    return [
        rounded_ratio(
            sum(weekday_values[day.weekday()]), len(weekday_values[day.weekday()])
        )
        for day in prediction_days
    ]


def forecast_collections(transactions, config, context=None, horizon_days=7) -> dict:
    if type(horizon_days) is not int or not 1 <= horizon_days <= 14:
        raise ValueError("Forecast horizon must be between 1 and 14 days")
    data = prepare(transactions, config, context)
    training = data.complete_days()
    result = {
        "status": "INSUFFICIENT_DATA",
        "method": "WEEKDAY_MEAN_BASELINE",
        "history_days": len(training),
        "forecast": [],
        "projected_total_paise": None,
        "limitations": [],
    }
    if data.end > data.today:
        result["limitations"].append(
            "Forecast origin cannot be a future reporting date."
        )
        return result
    prediction_days = [
        data.end + timedelta(days=offset) for offset in range(1, horizon_days + 1)
    ]
    predictions = weekday_predictions(data, training, prediction_days)
    if predictions is None:
        result["limitations"].append(
            "Forecast needs at least 28 complete past days and three complete observations for every predicted weekday. Unknown days are not zero."
        )
        return result
    result.update(
        status="AVAILABLE",
        forecast=[
            {"date": day.isoformat(), "collections_paise": value}
            for day, value in zip(prediction_days, predictions, strict=True)
        ],
    )
    result["projected_total_paise"] = sum(predictions)
    result["limitations"] = [
        "This weekday-mean baseline is an estimate, not guaranteed collections.",
        "No calibrated prediction interval or annual seasonality is established.",
    ]
    return result
