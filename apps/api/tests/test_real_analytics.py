"""Integration tests use explicitly labelled synthetic numerical fixtures, not merchant outcomes."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.services.analytics_adapter import Member3AnalyticsProvider

pytestmark = pytest.mark.postgres


def install_real_provider(app):
    app.state.analytics_provider = Member3AnalyticsProvider(require_calculations=True)


def import_canonical(client):
    amounts = [100000, 150000, 200000, 250000, 100000, 50000, 70000, 30000, 40000]
    statuses = ["SUCCESS"] * 6 + ["PENDING", "FAILED", "REFUNDED"]
    csv = "transaction_id,amount_paise,currency,timestamp,status\n"
    for index, (amount, status) in enumerate(zip(amounts, statuses, strict=True)):
        csv += f"TEST_{index},{amount},INR,2026-11-01T10:00:00+05:30,{status}\n"
    response = client.post(
        "/api/v1/transactions/import",
        files={
            "file": (
                "labelled-test-data.csv",
                csv.encode(),
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 9


def test_real_dashboard_and_trends_from_persisted_transactions(client_bundle):
    client, _actor, app = client_bundle
    install_real_provider(app)
    import_canonical(client)
    query = "?start_date=2026-11-01&end_date=2026-11-01"
    response = client.get("/api/v1/dashboard" + query)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "AVAILABLE"
    assert body["generation_mode"] == "REAL"
    assert body["result"]["collections_paise"] == 850000
    assert body["result"]["successful_count"] == 6
    assert body["result"]["average_payment_paise"] == 141667
    assert client.get("/api/v1/analytics" + query).json()["result"]["metrics"] == body["result"]


def test_real_forecast_and_evaluation_refuse_unknown_history(client_bundle):
    client, _actor, app = client_bundle
    install_real_provider(app)
    import_canonical(client)
    query = "?start_date=2026-11-01&end_date=2026-11-01"
    for endpoint in ["/forecast", "/forecast/evaluation"]:
        response = client.get("/api/v1" + endpoint + query)
        assert response.status_code == 200
        assert response.json()["status"] == "AVAILABLE"
        assert response.json()["result"]["status"] == "INSUFFICIENT_DATA"


def test_real_recommendation_needs_settings_and_preserves_terms(client_bundle):
    client, _actor, app = client_bundle
    install_real_provider(app)
    import_canonical(client)
    url = "/api/v1/recommendations/current?start_date=2026-11-01&end_date=2026-11-01"
    assert client.get(url).json()["result"]["suggested_action"] is None
    settings = {
        "type": "NTH_PAYMENT",
        "rule_parameters": {"n": 3},
        "reward_cost_paise": 10000,
        "budget_cap_paise": 10000,
        "duration_days": 1,
    }
    assert client.post("/api/v1/settings/promotion", json=settings).status_code == 200
    response = client.get(url)
    assert response.status_code == 200
    action = response.json()["result"]["suggested_action"]
    assert action["rule_parameters"] == {"n": 3}
    assert action["budget_cap_paise"] == 10000
    assert client.get("/api/v1/campaigns").json()["total"] == 0


@pytest.mark.parametrize("locale", ["en-IN", "hi-IN"])
def test_real_summary_is_grounded_and_language_selected(client_bundle, locale):
    client, _actor, app = client_bundle
    install_real_provider(app)
    import_canonical(client)
    response = client.get(f"/api/v1/summaries/daily?report_date=2026-11-01&locale={locale}")
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["locale"] == locale
    assert "₹8,500.00" in result["summary_text"]
    assert result["generation_mode"] == "DETERMINISTIC_FALLBACK"


def test_available_forecast_and_holdout_evaluation_through_postgres(client_bundle):
    client, _actor, app = client_bundle
    install_real_provider(app)
    end = datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata")).date() - timedelta(days=1)
    days = [end - timedelta(days=offset) for offset in reversed(range(35))]
    csv = "transaction_id,amount_paise,currency,timestamp,status\n"
    for index, day in enumerate(days):
        amount = (day.weekday() + 1) * 10000
        csv += f"HISTORY_{index},{amount},INR,{day.isoformat()}T12:00:00+05:30,SUCCESS\n"
    assert (
        client.post(
            "/api/v1/transactions/import",
            files={
                "file": (
                    "labelled-synthetic-history.csv",
                    csv.encode(),
                    "text/csv",
                )
            },
        ).status_code
        == 200
    )
    declarations = [
        {
            "date": day.isoformat(),
            "status": "COMPLETE",
            "provenance": "Explicit synthetic test-day declaration",
            "includes_simulated": True,
        }
        for day in days
    ]
    assert client.post("/api/v1/coverage", json={"items": declarations}).status_code == 200
    query = f"?start_date={days[0].isoformat()}&end_date={end.isoformat()}"
    response = client.get("/api/v1/forecast" + query)
    assert response.status_code == 200
    assert response.json()["result"]["status"] == "AVAILABLE"
    assert response.json()["result"]["projected_total_paise"] == 280000
    evaluation = client.get("/api/v1/forecast/evaluation" + query)
    assert evaluation.status_code == 200
    result = evaluation.json()["result"]
    assert result["training_days"] == 28
    assert result["mae_paise"] == 0
    assert result["flat_baseline_mae_paise"] == 17142.86
