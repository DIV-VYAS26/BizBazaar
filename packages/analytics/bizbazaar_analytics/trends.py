from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from .context import days_between, decimal_percent, money_text, prepare, rounded_ratio
from .metrics import calculate_metrics

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def analyze_trends(transactions, config, context=None) -> dict:
    data = prepare(transactions, config, context)
    metrics = calculate_metrics(transactions, config, context)
    totals = data.successful_totals()
    weekday_days = defaultdict(list)
    for day in data.complete_days():
        if day >= data.start:
            weekday_days[day.weekday()].append(day)
    eligible = {
        weekday: days for weekday, days in weekday_days.items() if len(days) >= 3
    }
    slow = []
    limitations = [
        "Weekday comparisons are descriptive associations, not causes or guaranteed growth."
    ]
    all_days = [day for dates in eligible.values() for day in dates]
    if len(eligible) >= 2:
        baseline_total = sum(totals[day] for day in all_days)
        for weekday, dates in sorted(eligible.items()):
            weekday_total = sum(totals[day] for day in dates)
            if weekday_total * len(all_days) < baseline_total * len(dates):
                mean = rounded_ratio(weekday_total, len(dates))
                slow.append(
                    {
                        "weekday": weekday,
                        "observed_complete_days": len(dates),
                        "explanation": f"{WEEKDAYS[weekday]} averaged {money_text(mean)} across {len(dates)} complete days, below the observed complete-day mean.",
                    }
                )
    else:
        limitations.append(
            "Slow-period comparisons require at least three complete observations for each of two weekdays."
        )
    end = min(data.end, data.today - timedelta(days=1))
    recent = days_between(end - timedelta(days=6), end)
    previous = days_between(end - timedelta(days=13), end - timedelta(days=7))
    complete = set(data.complete_days())
    decline = None
    if set(previous + recent) <= complete:
        old = [
            row.amount_paise
            for row, day in data.rows
            if row.status == "SUCCESS" and day in previous
        ]
        new = [
            row.amount_paise
            for row, day in data.rows
            if row.status == "SUCCESS" and day in recent
        ]
        if len(old) >= 5 and len(new) >= 5:
            old_average = Decimal(sum(old)) / len(old)
            new_average = Decimal(sum(new)) / len(new)
            decline = decimal_percent(old_average - new_average, old_average)
            if decline >= data.context.decline_threshold_percent:
                limitations.append(
                    f"Average payment declined {decline:.2f}% between the two consecutive complete seven-day windows; investigate before acting."
                )
        else:
            limitations.append(
                "Average-value comparison requires at least five successful payments in each seven-day window."
            )
    else:
        limitations.append(
            "Average-value comparison requires two consecutive complete seven-day windows."
        )
    return {
        "metrics": metrics,
        "slow_periods": slow,
        "average_value_decline_percent": decline,
        "limitations": limitations,
    }
