from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_commerce import customer, product, token_from_inbox

from app.db.commerce import EmailOutbox, Sale
from app.services.worker import deliver_one


def test_worker_preview_retry_and_suppression(business, database):
    client, _, app = business
    person = customer(client)
    client.post(f"/api/v1/customers/{person['id']}/portal-link")
    sent = []

    def sender(settings, row):
        sent.append(row.id)

    assert deliver_one(database, app.state.settings, sender) == "PREVIEW_ONLY"
    assert not sent
    app.state.settings.mail_delivery_mode = "smtp"

    def failure(settings, row):
        raise TimeoutError("Do not log SMTP secrets")

    assert deliver_one(database, app.state.settings, failure) == "RETRY"
    with Session(database) as db:
        row = db.scalar(select(EmailOutbox))
        row.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert deliver_one(database, app.state.settings, sender) == "SENT"
    assert len(sent) == 1
    assert deliver_one(database, app.state.settings, sender) == "IDLE"


def test_retention_consent_rechecked_and_due_reminders_deduplicated(business, database):
    client, _, app = business
    person = customer(client, request_marketing_consent=True)
    token = token_from_inbox(client, person["email"], "consent")
    client.post("/api/v1/public/consent", json=dict(token=token, decision="OPT_IN"))
    item = product(client)
    sale = client.post(
        "/api/v1/sales",
        json=dict(
            request_key="retention-sale",
            customer_id=person["id"],
            lines=[dict(product_id=item["id"], quantity=1)],
        ),
    ).json()
    with Session(database) as db:
        db.get(Sale, sale["id"]).created_at = datetime.now(UTC) - timedelta(days=40)
        db.commit()
    preview = client.get("/api/v1/retention/preview").json()
    assert len(preview) == 1
    draft = client.post(
        "/api/v1/retention/campaigns",
        json=dict(
            name="Test follow-up",
            subject="Test invitation",
            body="Synthetic test message",
            inactive_days=30,
            customer_ids=[person["id"]],
        ),
    )
    assert draft.status_code == 201, draft.text
    path = "/api/v1/retention/campaigns/" + draft.json()["id"]
    assert client.post(path + "/queue").status_code == 409
    assert client.post(path + "/approve").status_code == 200
    assert client.post(path + "/queue").json()["queued_count"] == 1
    assert client.post(path + "/queue").json()["queued_count"] == 1
    client.post(f"/api/v1/customers/{person['id']}/marketing-revoke")
    app.state.settings.mail_delivery_mode = "smtp"
    app.state.settings.marketing_delivery_enabled = True
    delivered = []
    for _ in range(5):
        deliver_one(database, app.state.settings, lambda settings, row: delivered.append(row.kind))
    assert "MARKETING" not in delivered
    with Session(database) as db:
        assert (
            db.scalar(select(EmailOutbox).where(EmailOutbox.kind == "MARKETING")).status
            == "SUPPRESSED"
        )
    overdue = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()
    client.post(
        f"/api/v1/credit/{person['id']}/charges",
        json=dict(request_key="due-1", amount_paise=10000, due_date=overdue),
    )
    assert "Queued 1" in client.post("/api/v1/credit/reminders/queue").json()["message"]
    assert "Queued 0" in client.post("/api/v1/credit/reminders/queue").json()["message"]


def test_loyalty_clawback_cannot_be_spent_again(business):
    client, _, _ = business
    person, item = customer(client), product(client)
    client.post(
        "/api/v1/loyalty/settings",
        json=dict(
            enabled=True,
            earning_spend_paise=10000,
            earning_points=1,
            point_value_paise=100,
            minimum_margin_bps=2000,
        ),
    )
    payload = dict(customer_id=person["id"], lines=[dict(product_id=item["id"], quantity=1)])
    first = client.post("/api/v1/sales", json=payload | {"request_key": "earn"}).json()
    assert (
        client.post(
            "/api/v1/sales", json=payload | {"request_key": "spend", "redeem_points": 4}
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/sales/{first['id']}/void", json=dict(request_key="void-earn", note="Returned")
        ).status_code
        == 200
    )
    balance = client.get(f"/api/v1/loyalty/{person['id']}").json()
    assert balance["balance_points"] == -1 and balance["available_points"] == 0
    assert (
        client.post(
            "/api/v1/sales", json=payload | {"request_key": "overspend", "redeem_points": 1}
        ).status_code
        == 409
    )
