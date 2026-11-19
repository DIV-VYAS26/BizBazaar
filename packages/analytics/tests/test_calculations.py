"""Labelled numerical test fixtures, not real merchant records or measured business outcomes."""

import copy
import json
from datetime import UTC, date, datetime, timedelta

import pytest
from bizbazaar_analytics import (
    analyze_trends,
    calculate_metrics,
    evaluate_forecast,
    forecast_collections,
    generate_daily_summary,
    recommend_campaign,
)
from bizbazaar_analytics.ai.external import ExternalStyleProvider
from bizbazaar_analytics.api import run
from bizbazaar_analytics.schemas import TransactionInput
from pydantic import ValidationError


def canonical():
    amounts = [100000, 150000, 200000, 250000, 100000, 50000, 70000, 30000, 40000]
    statuses = ["SUCCESS"] * 6 + ["PENDING", "FAILED", "REFUNDED"]
    rows = [
        {
            "merchant_id": "test_merchant",
            "transaction_id": f"TXN{i}",
            "amount_paise": amount,
            "timestamp": "2026-11-01T10:00:00+05:30",
            "status": status,
        }
        for i, (amount, status) in enumerate(zip(amounts, statuses, strict=True))
    ]
    config = {
        "start_date": "2026-11-01",
        "end_date": "2026-11-01",
        "timezone": "Asia/Kolkata",
    }
    context = {"as_of_timestamp": "2026-11-06T00:00:00Z"}
    return rows, config, context


def history(count=42):
    start = date(2026, 8, 3)  # Monday. Each weekday has a distinct known amount.
    days = [start + timedelta(days=i) for i in range(count)]
    rows = [
        {
            "merchant_id": "test_merchant",
            "transaction_id": f"history_{i}",
            "amount_paise": (day.weekday() + 1) * 10000,
            "timestamp": datetime.combine(
                day, datetime.min.time(), tzinfo=UTC
            ).isoformat(),
            "status": "SUCCESS",
        }
        for i, day in enumerate(days)
    ]
    config = {
        "start_date": start.isoformat(),
        "end_date": days[-1].isoformat(),
        "timezone": "Asia/Kolkata",
    }
    context = {
        "as_of_timestamp": "2026-10-01T00:00:00Z",
        "coverage": [
            {
                "date": day.isoformat(),
                "status": "COMPLETE",
                "provenance": "Explicit synthetic test-day coverage",
            }
            for day in days
        ],
    }
    return rows, config, context


def settings(**changes):
    return {
        "type": "NTH_PAYMENT",
        "rule_parameters": {"n": 3},
        "reward_cost_paise": 10000,
        "budget_cap_paise": 20000,
        "duration_days": 2,
    } | changes


def test_canonical_metrics_independently_known_values():
    rows, config, context = canonical()
    result = calculate_metrics(rows, config, context)
    assert result["collections_paise"] == 850000
    assert result["successful_count"] == 6
    assert result["average_payment_paise"] == 141667
    assert result["status_counts"] == {
        "success": 6,
        "pending": 1,
        "failed": 1,
        "refunded": 1,
    }


def test_half_up_average_and_empty_average():
    rows, config, context = canonical()
    rows = rows[:2]
    rows[0]["amount_paise"], rows[1]["amount_paise"] = 1, 2
    assert calculate_metrics(rows, config, context)["average_payment_paise"] == 2
    empty = calculate_metrics([], config, context)
    assert (
        empty["collections_paise"],
        empty["successful_count"],
        empty["average_payment_paise"],
    ) == (0, 0, None)
    assert empty["daily_collections"] == []


def test_local_midnight_and_inclusive_reporting_bounds():
    rows, _, context = canonical()
    rows = rows[:2]
    rows[0]["timestamp"], rows[1]["timestamp"] = (
        "2026-11-01T18:29:59Z",
        "2026-11-01T18:30:00Z",
    )
    config = {
        "start_date": "2026-11-02",
        "end_date": "2026-11-02",
        "timezone": "Asia/Kolkata",
    }
    context["history_start_date"] = "2026-11-01"
    result = calculate_metrics(rows, config, context)
    assert result["collections_paise"] == 150000
    assert result["successful_count"] == 1


def test_unknown_empty_day_is_not_a_complete_zero_day():
    _, config, context = canonical()
    assert calculate_metrics([], config, context)["daily_collections"] == []
    context["coverage"] = [
        {
            "date": "2026-11-01",
            "status": "COMPLETE",
            "provenance": "Declared test coverage",
        }
    ]
    assert calculate_metrics([], config, context)["daily_collections"] == [
        {"date": "2026-11-01", "collections_paise": 0, "successful_count": 0}
    ]


@pytest.mark.parametrize("amount", [0, -1, True, 1.5, "100", 1000000000001])
def test_canonical_amount_domain_is_strict(amount):
    rows, _, _ = canonical()
    with pytest.raises(ValidationError):
        TransactionInput.model_validate(rows[0] | {"amount_paise": amount})


@pytest.mark.parametrize("identifier", ["embedded\nnewline", "NUL\x00", "a" * 101])
def test_control_characters_and_oversized_identifiers_are_rejected(identifier):
    rows, _, _ = canonical()
    with pytest.raises(ValidationError):
        TransactionInput.model_validate(rows[0] | {"transaction_id": identifier})


def test_batch_rejects_duplicates_and_mixed_merchants():
    rows, config, context = canonical()
    with pytest.raises(ValueError, match="Duplicate"):
        calculate_metrics([rows[0], rows[0]], config, context)
    with pytest.raises(ValueError, match="one merchant"):
        calculate_metrics(
            [rows[0], rows[1] | {"merchant_id": "other"}], config, context
        )


def test_forecast_requires_coverage_not_just_transaction_count():
    rows, config, context = history()
    context["coverage"] = []
    result = forecast_collections(rows, config, context)
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["forecast"] == []
    assert result["projected_total_paise"] is None


def test_forecast_28_day_boundary_and_exact_weekday_values():
    rows, config, context = history(27)
    assert forecast_collections(rows, config, context)["status"] == "INSUFFICIENT_DATA"
    rows, config, context = history(28)
    result = forecast_collections(rows, config, context)
    assert result["status"] == "AVAILABLE"
    assert [point["collections_paise"] for point in result["forecast"]] == [
        10000,
        20000,
        30000,
        40000,
        50000,
        60000,
        70000,
    ]
    assert result["projected_total_paise"] == 280000


def test_current_day_cannot_train_forecast_even_if_declared_complete():
    rows, config, context = history(28)
    context["as_of_timestamp"] = config["end_date"] + "T10:00:00Z"
    result = forecast_collections(rows, config, context)
    assert result["history_days"] == 27
    assert result["status"] == "INSUFFICIENT_DATA"


def test_complete_zero_activity_is_a_valid_forecast_observation():
    _rows, config, context = history(28)
    result = forecast_collections([], config, context)
    assert result["status"] == "AVAILABLE"
    assert result["projected_total_paise"] == 0


def test_evaluation_has_independent_known_errors():
    rows, config, context = history(35)
    result = evaluate_forecast(rows, config, context)
    assert result["status"] == "AVAILABLE"
    assert result["training_days"] == 28
    assert result["holdout_days"] == 7
    assert result["mae_paise"] == 0
    assert result["flat_baseline_mae_paise"] == 17142.86


def test_holdout_values_cannot_leak_into_training_predictions():
    rows, config, context = history(35)
    before = evaluate_forecast(rows, config, context)
    changed = copy.deepcopy(rows)
    for row in changed[-7:]:
        row["amount_paise"] *= 10
    after = evaluate_forecast(changed, config, context)
    assert [row["predicted_paise"] for row in before["holdout"]] == [
        row["predicted_paise"] for row in after["holdout"]
    ]
    assert after["mae_paise"] == 360000


def test_evaluation_refuses_incomplete_calendar_holdout():
    rows, config, context = history(35)
    context["coverage"].pop(-3)
    assert evaluate_forecast(rows, config, context)["status"] == "INSUFFICIENT_DATA"


def test_slow_weekday_requires_enough_complete_observations():
    rows, config, context = history(42)
    for row in rows:
        day = datetime.fromisoformat(row["timestamp"]).weekday()
        row["amount_paise"] = 10000 if day == 0 else 20000
    result = analyze_trends(rows, config, context)
    assert [point["weekday"] for point in result["slow_periods"]] == [0]
    assert result["slow_periods"][0]["observed_complete_days"] == 6


def test_average_decline_uses_two_consecutive_complete_windows():
    rows, config, context = history(14)
    for index, row in enumerate(rows):
        row["amount_paise"] = 20000 if index < 7 else 10000
    result = analyze_trends(rows, config, context)
    assert result["average_value_decline_percent"] == 50
    context["coverage"].pop(5)
    assert (
        analyze_trends(rows, config, context)["average_value_decline_percent"] is None
    )


def test_decline_alert_threshold_is_configurable_without_changing_metrics():
    rows, config, context = history(14)
    for index, row in enumerate(rows):
        row["amount_paise"] = 20000 if index < 7 else 10000
    context["decline_threshold_percent"] = 60
    result = analyze_trends(rows, config, context)
    assert result["average_value_decline_percent"] == 50
    assert not any(
        "investigate before acting" in note for note in result["limitations"]
    )


def test_recommendation_copies_merchant_terms_and_does_not_activate():
    rows, config, context = canonical()
    result = recommend_campaign(rows, config, settings(), context)
    action = result["suggested_action"]
    assert action["rule_parameters"] == {"n": 3}
    assert action["reward_cost_paise"] == 10000
    assert action["budget_cap_paise"] == 20000
    assert "status" not in action
    assert (
        recommend_campaign([], config, settings(), context)["suggested_action"] is None
    )
    with pytest.raises(ValidationError):
        recommend_campaign(rows, config, settings(budget_cap_paise=1), context)


def test_summaries_use_calculated_numbers_in_both_languages():
    rows, config, context = canonical()
    english = generate_daily_summary(rows, config, context)
    hindi = generate_daily_summary(rows, config, context, locale="hi-IN")
    for result in [english, hindi]:
        assert "₹8,500.00" in result["summary_text"]
        assert "₹1,416.67" in result["summary_text"]
        assert "2026-11-01" in result["summary_text"]
        assert result["generation_mode"] == "DETERMINISTIC_FALLBACK"
    assert "दर्ज" in hindi["summary_text"]


@pytest.mark.parametrize(
    "response", [{"text": "Invented ₹999999"}, {"style": "unknown"}, None]
)
def test_invalid_optional_ai_output_falls_back_without_fabricated_text(response):
    rows, config, context = canonical()
    provider = ExternalStyleProvider(lambda facts: response)
    result = generate_daily_summary(rows, config, context, provider=provider)
    assert result["generation_mode"] == "DETERMINISTIC_FALLBACK"
    assert "999999" not in result["summary_text"]


def test_timeout_from_optional_provider_preserves_verified_summary():
    rows, config, context = canonical()

    def timeout(facts):
        raise TimeoutError()

    result = generate_daily_summary(
        rows, config, context, provider=ExternalStyleProvider(timeout)
    )
    assert result["generation_mode"] == "DETERMINISTIC_FALLBACK"
    assert "₹8,500.00" in result["summary_text"]


@pytest.mark.parametrize(
    "operation",
    ["dashboard", "analytics", "forecast", "evaluation", "recommendation", "summary"],
)
def test_entry_point_returns_serializable_json(operation):
    rows, config, context = canonical()
    result = run(
        operation,
        {
            "transactions": rows,
            "config": config,
            "context": context,
            "merchant_settings": settings(),
        },
    )
    assert isinstance(json.dumps(result, allow_nan=False), str)
