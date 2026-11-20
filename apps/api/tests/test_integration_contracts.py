import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog
from app.services.analytics_adapter import Member3AnalyticsProvider

pytestmark = pytest.mark.postgres


def declaration(**changes):
    return {
        "date": "2026-11-01",
        "status": "COMPLETE",
        "provenance": "Merchant-declared export coverage",
        "includes_simulated": True,
    } | changes


def test_coverage_declarations_are_scoped_and_audited(client_bundle, database):
    client, actor, app = client_bundle
    assert client.post("/api/v1/coverage", json={"items": [declaration()]}).status_code == 200
    query = "/api/v1/coverage?start_date=2026-11-01&end_date=2026-11-01"
    assert len(client.get(query).json()) == 1
    assert client.get(query + "&includes_simulated=false").json() == []
    with Session(database) as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "COVERAGE_DECLARED")) is not None


def test_new_import_invalidates_previous_complete_coverage(client_bundle):
    client, actor, app = client_bundle
    for scope in [True, False]:
        response = client.post(
            "/api/v1/coverage", json={"items": [declaration(includes_simulated=scope)]}
        )
        assert response.status_code == 200
    response = client.post(
        "/api/v1/transactions/import",
        files={
            "file": (
                "test.csv",
                b"transaction_id,amount_paise,currency,timestamp,status\n"
                b"coverage-change,10000,INR,2026-11-01T10:00:00Z,SUCCESS\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    for scope in ["true", "false"]:
        rows = client.get(
            "/api/v1/coverage?start_date=2026-11-01&end_date=2026-11-01"
            + "&includes_simulated="
            + scope
        ).json()
        assert rows[0]["status"] == "PARTIAL"


def test_coverage_and_settings_require_authorization_and_csrf(client_bundle):
    client, actor, app = client_bundle
    client.headers.pop("X-CSRF-Token")
    assert client.post("/api/v1/coverage", json={"items": [declaration()]}).status_code == 403


def test_coverage_rejects_duplicate_dates_and_future_complete_day(client_bundle):
    client, actor, app = client_bundle
    assert (
        client.post("/api/v1/coverage", json={"items": [declaration(), declaration()]}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/coverage", json={"items": [declaration(date="2100-01-01")]}
        ).status_code
        == 422
    )


def test_merchant_configured_promotion_settings(client_bundle):
    client, actor, app = client_bundle
    payload = {
        "type": "NTH_PAYMENT",
        "rule_parameters": {"n": 3},
        "reward_cost_paise": 10000,
        "budget_cap_paise": 20000,
        "duration_days": 2,
    }
    assert client.get("/api/v1/settings/promotion").json() is None
    assert client.post("/api/v1/settings/promotion", json=payload).json() == payload
    assert client.get("/api/v1/settings/promotion").json() == payload
    assert (
        client.post(
            "/api/v1/settings/promotion", json=payload | {"rule_parameters": {"n": True}}
        ).status_code
        == 422
    )


def test_actual_member3_models_accept_backend_inputs(client_bundle):
    client, actor, app = client_bundle
    provider = Member3AnalyticsProvider()
    captured = []
    original = provider.validate_inputs

    def validate(dataset):
        captured.append(dataset)
        return original(dataset)

    provider.validate_inputs = validate
    app.state.analytics_provider = provider
    response = client.get("/api/v1/dashboard?start_date=2026-11-01&end_date=2026-11-06")
    assert response.status_code == 200
    assert response.json()["status"] == "UNAVAILABLE"
    assert "foundation mode" in " ".join(response.json()["limitations"])
    assert set(captured[0]["config"]) == {"start_date", "end_date", "timezone"}
    assert "coverage" in captured[0]["context"]


def test_invalid_provider_output_is_rejected_without_exposing_it(client_bundle):
    client, actor, app = client_bundle

    class BrokenProvider:
        def run(self, operation, dataset):
            return {"private_provider_error": "must-not-leak"}

    app.state.analytics_provider = BrokenProvider()
    response = client.get("/api/v1/dashboard?start_date=2026-11-01&end_date=2026-11-06")
    assert response.status_code == 503
    assert "must-not-leak" not in response.text
