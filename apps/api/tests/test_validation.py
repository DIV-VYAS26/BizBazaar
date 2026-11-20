from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.schemas.api import CampaignCreate, SimulationPayment


def campaign_payload(**changes):
    now = datetime.now(UTC)
    data = {
        "name": "Afternoon reward",
        "type": "NTH_PAYMENT",
        "rule_parameters": {"n": 3},
        "reward_cost_paise": 10000,
        "budget_cap_paise": 10000,
        "starts_at": (now - timedelta(minutes=1)).isoformat(),
        "ends_at": (now + timedelta(hours=1)).isoformat(),
    }
    return data | changes


@pytest.mark.parametrize(
    "changes",
    [
        {"merchant_id": "injected"},
        {"status": "ACTIVE"},
        {"consumed_paise": 0},
        {"reward_cost_paise": True},
        {"reward_cost_paise": 1.5},
        {"rule_parameters": {"n": 0}},
        {"rule_parameters": {"threshold_paise": 100}},
        {"budget_cap_paise": 9999},
        {"starts_at": "2026-01-01T00:00:00"},
    ],
)
def test_campaign_rejects_invalid_or_server_owned_fields(changes):
    with pytest.raises(ValidationError):
        CampaignCreate(**campaign_payload(**changes))


def test_simulator_does_not_accept_source_or_ownership():
    with pytest.raises(ValidationError):
        SimulationPayment(
            event_id="event",
            transaction_id="txn",
            amount_paise=100,
            timestamp=datetime.now(UTC),
            is_simulated=False,
        )


def test_public_production_is_blocked_until_real_identity_exists():
    with pytest.raises(ValidationError):
        Settings(app_env="production")


def test_health_and_auth_errors_have_request_ids():
    with TestClient(create_app(Settings())) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["service"] == "bizbazaar-api"
        response = client.get("/api/v1/session")
        assert response.status_code == 401
        assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


def test_request_body_limit_runs_before_parsing():
    with TestClient(create_app(Settings(max_body_bytes=1024))) as client:
        response = client.post("/api/v1/demo/session", content=b"x" * 1025)
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "BODY_TOO_LARGE"


def test_validation_errors_do_not_reflect_credentials():
    with TestClient(create_app(Settings(demo_enabled=True))) as client:
        response = client.post("/api/v1/demo/session", json={"token": "private-secret"})
        assert response.status_code == 422
        assert "private-secret" not in response.text


def test_cross_origin_is_not_permitted():
    with TestClient(create_app(Settings())) as client:
        response = client.options(
            "/api/v1/campaigns",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert "access-control-allow-origin" not in response.headers
