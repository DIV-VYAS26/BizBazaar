from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from conftest import add_actor
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_validation import campaign_payload

from app.core.config import Settings
from app.core.errors import ApiError
from app.db.models import (
    AuditLog,
    Campaign,
    Coverage,
    DemoSession,
    PaymentEvent,
    ProcessedTransaction,
    Reward,
    Transaction,
)
from app.schemas.api import CampaignCreate, SimulationPayment
from app.services import rewards as reward_service
from app.services.campaigns import create_campaign, transition_campaign
from app.services.csv_import import import_csv
from app.services.rewards import simulate_payment, simulate_refund

pytestmark = pytest.mark.postgres


def active_campaign(engine, actor, **changes):
    with Session(engine) as db:
        row = create_campaign(db, actor, CampaignCreate(**campaign_payload(**changes)))
        transition_campaign(db, actor, row.id, "approve")
        return transition_campaign(db, actor, row.id, "activate")


def payment(number=1, **changes):
    return SimulationPayment(
        **(
            {
                "event_id": f"event{number}",
                "transaction_id": f"txn{number}",
                "amount_paise": 10000,
                "timestamp": datetime.now(UTC),
                "status": "SUCCESS",
            }
            | changes
        )
    )


def send(engine, actor, payload):
    with Session(engine) as db:
        return simulate_payment(db, actor, payload)


def test_nth_budget_replay_and_refund(database, actor):
    campaign = active_campaign(database, actor)
    amounts = [100000, 150000, 200000, 250000, 100000, 50000]
    inputs = [payment(i, amount_paise=amount) for i, amount in enumerate(amounts, 1)]
    results = [send(database, actor, item) for item in inputs]
    assert results[2].decision == "ISSUED"
    assert results[5].decision == "SKIPPED_BUDGET"
    assert send(database, actor, inputs[2]) == results[2]
    with Session(database) as db:
        row = db.get(Campaign, campaign.id)
        assert row.eligible_count == 6
        assert row.cumulative_paise == 850000
        assert row.consumed_paise == 10000
        txn = db.scalar(select(Transaction).where(Transaction.transaction_id == "txn3"))
        simulate_refund(db, actor, txn.id)
        assert db.scalar(select(func.count()).select_from(Reward)) == 1
        assert db.get(Campaign, campaign.id).cumulative_paise == 850000


def test_threshold_exact_crossing_once(database, actor):
    active_campaign(
        database,
        actor,
        type="COLLECTION_THRESHOLD",
        rule_parameters={"threshold_paise": 800000},
        budget_cap_paise=100000,
    )
    results = [
        send(database, actor, payment(i, amount_paise=amount))
        for i, amount in enumerate([100000, 150000, 200000, 250000, 100000, 50000], 1)
    ]
    assert [result.decision for result in results].count("ISSUED") == 1
    assert results[4].decision == "ISSUED"


def test_same_event_race_returns_identical_decisions(database, actor):
    active_campaign(database, actor, rule_parameters={"n": 1})
    payload = payment()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: send(database, actor, payload), range(4)))
    assert all(result == results[0] for result in results)
    with Session(database) as db:
        assert db.scalar(select(func.count()).select_from(Reward)) == 1
        assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 1
        assert db.scalar(select(func.count()).select_from(ProcessedTransaction)) == 1


def test_final_budget_race(database, actor):
    campaign = active_campaign(database, actor, rule_parameters={"n": 1})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda n: send(database, actor, payment(n)), [1, 2]))
    assert sorted(result.decision for result in results) == ["ISSUED", "SKIPPED_BUDGET"]
    with Session(database) as db:
        assert db.get(Campaign, campaign.id).consumed_paise == 10000


def test_duplicate_transaction_different_event_does_not_advance(database, actor):
    campaign = active_campaign(database, actor)
    original = payment()
    send(database, actor, original)
    with pytest.raises(ApiError) as error:
        send(database, actor, original.model_copy(update={"event_id": "different"}))
    assert error.value.status == 409
    with Session(database) as db:
        assert db.get(Campaign, campaign.id).eligible_count == 1


def test_conflicting_event_does_not_mutate(database, actor):
    active_campaign(database, actor)
    original = payment()
    send(database, actor, original)
    with pytest.raises(ApiError, match="different payload"):
        send(database, actor, original.model_copy(update={"amount_paise": 900}))


def test_failure_rolls_back_all_event_writes(database, actor, monkeypatch):
    campaign = active_campaign(database, actor, rule_parameters={"n": 1})

    def fail(*args, **kwargs):
        raise RuntimeError("injected failure")

    monkeypatch.setattr(reward_service, "audit", fail)
    with pytest.raises(RuntimeError, match="injected"):
        send(database, actor, payment())
    with Session(database) as db:
        assert db.get(Campaign, campaign.id).eligible_count == 0
        assert db.get(Campaign, campaign.id).consumed_paise == 0
        for model in [PaymentEvent, Reward, ProcessedTransaction, Transaction]:
            assert db.scalar(select(func.count()).select_from(model)) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "PAYMENT_SIMULATED")
            )
            == 0
        )


def test_concurrent_activation_has_only_one_winner(database, actor):
    with Session(database) as db:
        rows = [create_campaign(db, actor, CampaignCreate(**campaign_payload())) for _ in range(2)]
        for row in rows:
            transition_campaign(db, actor, row.id, "approve")

    def activate(row):
        with Session(database) as db:
            try:
                return transition_campaign(db, actor, row.id, "activate").status
            except ApiError as exc:
                return exc.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(activate, rows))
    assert results.count("ACTIVE") == 1
    assert results.count(409) == 1


def test_expired_active_does_not_block_replacement(database, actor):
    old = active_campaign(database, actor)
    with Session(database) as db:
        row = db.get(Campaign, old.id)
        row.starts_at = datetime.now(UTC) - timedelta(hours=2)
        row.ends_at = datetime.now(UTC) - timedelta(hours=1)
        db.commit()
    replacement = active_campaign(database, actor)
    with Session(database) as db:
        assert db.get(Campaign, old.id).status == "COMPLETED"
        assert db.get(Campaign, replacement.id).status == "ACTIVE"


@pytest.mark.parametrize("status", ["PENDING", "FAILED", "REFUNDED"])
def test_unsuccessful_transactions_do_not_advance(database, actor, status):
    campaign = active_campaign(database, actor)
    assert send(database, actor, payment(status=status)).decision == "NOT_ELIGIBLE"
    with Session(database) as db:
        assert db.get(Campaign, campaign.id).eligible_count == 0


def test_replay_after_completion_and_new_campaign(database, actor):
    first = active_campaign(database, actor, rule_parameters={"n": 1})
    payload = payment()
    original = send(database, actor, payload)
    with Session(database) as db:
        transition_campaign(db, actor, first.id, "complete")
    second = active_campaign(database, actor, rule_parameters={"n": 1})
    assert send(database, actor, payload) == original
    with Session(database) as db:
        assert db.get(Campaign, second.id).eligible_count == 0


def test_import_validation_duplicates_conflicts_and_isolation(database, actor):
    content = (
        b"transaction_id,amount_paise,currency,timestamp,status\n"
        b"A,100000,INR,2026-11-01T10:00:00+05:30,SUCCESS\n"
        b"A,100000,INR,2026-11-01T10:00:00+05:30,SUCCESS\n"
        b"B,-1,INR,2026-11-01T10:00:00+05:30,SUCCESS\n"
        b"A,200000,INR,2026-11-01T10:00:00+05:30,SUCCESS\n"
    )
    with Session(database) as db:
        result = import_csv(db, actor, content, Settings())
        assert (result.imported, result.duplicates, result.invalid, result.conflicts) == (
            1,
            1,
            1,
            1,
        )
    other, _, _ = add_actor(database, "Other shop")
    with Session(database) as db:
        assert import_csv(db, other, content, Settings()).imported == 1


def test_api_tenant_isolation_csrf_and_reports(client_bundle, database):
    client, actor, app = client_bundle
    other, _, _ = add_actor(database, "Other")
    foreign = active_campaign(database, other)
    assert client.get(f"/api/v1/campaigns/{foreign.id}").status_code == 404
    assert client.post(f"/api/v1/campaigns/{foreign.id}/approve").status_code == 404
    assert client.get(f"/api/v1/campaigns/{foreign.id}/report").status_code == 404
    assert client.get("/api/v1/campaigns").json()["total"] == 0
    client.headers.pop("X-CSRF-Token")
    assert client.post("/api/v1/campaigns", json=campaign_payload()).status_code == 403


def test_analytics_unavailable_is_honest_and_range_is_bounded(client_bundle):
    client, actor, app = client_bundle
    response = client.get("/api/v1/analytics?start_date=2026-11-01&end_date=2026-11-06")
    assert response.status_code == 200
    assert response.json()["status"] == "UNAVAILABLE"
    assert response.json()["result"] is None
    assert (
        client.get("/api/v1/analytics?start_date=2020-01-01&end_date=2026-11-06").status_code == 422
    )
    assert (
        client.get("/api/v1/analytics?start_date=0001-01-01&end_date=0001-01-02").status_code == 422
    )


def test_analytics_adapter_includes_coverage_history_and_local_dates(client_bundle, database):
    client, actor, app = client_bundle
    captured = {}

    class Provider:
        def run(self, operation, dataset):
            captured.update(dataset)
            return {
                "metrics": {
                    "collections_paise": 0,
                    "successful_count": 0,
                    "average_payment_paise": None,
                    "status_counts": {"success": 0, "pending": 0, "failed": 0, "refunded": 0},
                    "daily_collections": [],
                    "weekday_collections": [],
                    "warnings": [],
                },
                "slow_periods": [],
                "average_value_decline_percent": None,
                "limitations": [],
            }

    app.state.analytics_provider = Provider()
    with Session(database) as db:
        db.add(
            Coverage(
                merchant_id=actor.merchant_id,
                date=datetime(2026, 11, 1).date(),
                status="COMPLETE",
                provenance="test-declared demo coverage",
            )
        )
        db.commit()
    response = client.get("/api/v1/analytics?start_date=2026-11-01&end_date=2026-11-06")
    assert response.status_code == 200
    assert captured["context"]["coverage"][0]["status"] == "COMPLETE"
    assert captured["context"]["history_start_date"] < "2026-11-01"


def test_audit_update_delete_are_rejected(database, actor):
    active_campaign(database, actor)
    for operation in ["UPDATE audit_logs SET action='changed'", "DELETE FROM audit_logs"]:
        with Session(database) as db, pytest.raises(DBAPIError):
            db.execute(text(operation))
            db.commit()


def test_expired_revoked_sessions_and_logout(client_bundle, database):
    client, actor, app = client_bundle
    assert client.get("/api/v1/session").status_code == 200
    assert client.post("/api/v1/session/logout").status_code == 200
    assert client.get("/api/v1/session").status_code == 401
    with Session(database) as db:
        assert db.get(DemoSession, actor.session_id).revoked


def test_same_transaction_different_event_race(database, actor):
    campaign = active_campaign(database, actor, rule_parameters={"n": 1})
    original = payment()

    def process(event_id):
        try:
            return send(
                database, actor, original.model_copy(update={"event_id": event_id})
            ).decision
        except ApiError as exc:
            return exc.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(process, ["first", "second"]))
    assert results.count("ISSUED") == 1
    assert results.count(409) == 1
    with Session(database) as db:
        assert db.get(Campaign, campaign.id).eligible_count == 1


def test_completion_racing_payment_has_consistent_outcome(database, actor):
    campaign = active_campaign(database, actor, rule_parameters={"n": 1})

    def complete():
        with Session(database) as db:
            return transition_campaign(db, actor, campaign.id, "complete")

    with ThreadPoolExecutor(max_workers=2) as pool:
        completion = pool.submit(complete)
        event = pool.submit(send, database, actor, payment())
        assert completion.result().status == "COMPLETED"
        decision = event.result().decision
    with Session(database) as db:
        row = db.get(Campaign, campaign.id)
        assert row.status == "COMPLETED"
        assert row.eligible_count == (1 if decision == "ISSUED" else 0)
        assert decision in {"ISSUED", "CAMPAIGN_INACTIVE"}


def test_time_is_rechecked_after_waiting_for_lock(database, actor, monkeypatch):
    from threading import Event

    from app.core.security import lock_merchant

    campaign = active_campaign(database, actor, rule_parameters={"n": 1})
    entered = Event()

    def notify_then_lock(db, current_actor):
        entered.set()
        return lock_merchant(db, current_actor)

    monkeypatch.setattr(reward_service, "lock_merchant", notify_then_lock)
    with Session(database) as blocker:
        lock_merchant(blocker, actor)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(send, database, actor, payment())
            assert entered.wait(timeout=5)
            # Simulate clock reaching the exclusive expiry boundary while request waits.
            monkeypatch.setattr(reward_service, "now_utc", lambda: campaign.ends_at)
            blocker.commit()
            assert future.result(timeout=5).decision == "CAMPAIGN_INACTIVE"
    with Session(database) as db:
        assert db.get(Campaign, campaign.id).status == "COMPLETED"
        assert db.scalar(select(func.count()).select_from(Reward)) == 0


def test_demo_credential_exchange_is_one_time_and_tokens_not_returned(client_bundle, database):
    client, actor, app = client_bundle
    _, credential, _ = add_actor(database, "Login shop")
    response = client.post("/api/v1/demo/session", json={"token": credential})
    assert response.status_code == 200
    assert credential not in response.text
    assert "token" not in response.json()
    assert "HttpOnly" in response.headers.get_list("set-cookie")[0]
    assert client.post("/api/v1/demo/session", json={"token": credential}).status_code == 401


def test_full_api_campaign_journey(client_bundle):
    client, actor, app = client_bundle
    response = client.post(
        "/api/v1/transactions/import",
        files={
            "file": (
                "history.csv",
                b"transaction_id,amount_paise,currency,timestamp,status\n"
                b"historical,100000,INR,2026-11-01T10:00:00Z,SUCCESS\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 1
    created = client.post("/api/v1/campaigns", json=campaign_payload(rule_parameters={"n": 1}))
    assert created.status_code == 201
    campaign_id = created.json()["id"]
    assert client.post(f"/api/v1/campaigns/{campaign_id}/activate").status_code == 409
    assert client.post(f"/api/v1/campaigns/{campaign_id}/approve").status_code == 200
    assert client.post(f"/api/v1/campaigns/{campaign_id}/activate").status_code == 200
    payload = payment().model_dump(mode="json")
    issued = client.post("/api/v1/simulations/payments", json=payload)
    assert issued.status_code == 200
    assert issued.json()["decision"] == "ISSUED"
    assert client.post("/api/v1/simulations/payments", json=payload).json() == issued.json()
    report = client.get(f"/api/v1/campaigns/{campaign_id}/report").json()
    assert report["issued_count"] == 1
    assert report["remaining_budget_paise"] == 0
    assert client.get("/api/v1/rewards").json()["total"] == 1
