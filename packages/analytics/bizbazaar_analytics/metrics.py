from collections import Counter, defaultdict

from .context import days_between, prepare, rounded_ratio


def calculate_metrics(transactions, config, context=None) -> dict:
    data = prepare(transactions, config, context)
    rows = [(row, day) for row, day in data.rows if data.start <= day <= data.end]
    counts = Counter(row.status for row, _ in rows)
    total = sum(row.amount_paise for row, _ in rows if row.status == "SUCCESS")
    daily_amount, daily_count, observed_dates = (
        defaultdict(int),
        defaultdict(int),
        set(),
    )
    weekday_amount = defaultdict(int)
    for row, day in rows:
        observed_dates.add(day)
        if row.status == "SUCCESS":
            daily_amount[day] += row.amount_paise
            daily_count[day] += 1
            weekday_amount[day.weekday()] += row.amount_paise
    complete = [day for day in data.complete_days() if data.start <= day <= data.end]
    daily_dates = observed_dates | set(complete)
    complete_weekdays = Counter(day.weekday() for day in complete)
    missing = len(days_between(data.start, data.end)) - len(complete)
    warnings = ["Totals describe recorded collections, not total shop sales or profit."]
    if not counts["SUCCESS"]:
        warnings.append(
            "No successful payments were recorded in this period; average is unavailable."
        )
    if missing:
        warnings.append(
            f"{missing} reporting day(s) are partial or have unknown coverage; omitted activity cannot be inferred."
        )
    if data.context.includes_simulated:
        warnings.append(
            "This report includes any simulated transactions in the selected dataset."
        )
    return {
        "collections_paise": total,
        "successful_count": counts["SUCCESS"],
        "average_payment_paise": rounded_ratio(total, counts["SUCCESS"])
        if counts["SUCCESS"]
        else None,
        "status_counts": {
            status.lower(): counts[status]
            for status in ["SUCCESS", "PENDING", "FAILED", "REFUNDED"]
        },
        "daily_collections": [
            {
                "date": day.isoformat(),
                "collections_paise": daily_amount[day],
                "successful_count": daily_count[day],
            }
            for day in sorted(daily_dates)
        ],
        "weekday_collections": [
            {
                "weekday": weekday,
                "collections_paise": weekday_amount[weekday],
                "observed_complete_days": complete_weekdays[weekday],
            }
            for weekday in range(7)
        ],
        "warnings": warnings,
    }
