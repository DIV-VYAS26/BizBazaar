import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db.commerce import Product, SaleLine
from app.schemas.commerce import SaleCreate
from app.services.sales import record_sale


def product(client, **overrides):
    payload = dict(
        sku=uuid4().hex,
        name="Test rice",
        selling_price_paise=40000,
        unit_cost_paise=20000,
        stock_quantity=20,
        active=True,
    )
    response = client.post("/api/v1/products", json=payload | overrides)
    assert response.status_code == 201, response.text
    return response.json()


def customer(client, **overrides):
    response = client.post(
        "/api/v1/customers",
        json=dict(name="Test customer", email="customer@example.com") | overrides,
    )
    assert response.status_code == 201, response.text
    return response.json()


def token_from_inbox(client, email, flow):
    response = client.get("/api/v1/auth/dev-inbox", params={"email": email})
    assert response.status_code == 200, response.text
    return next(
        re.search(r"token=([\w-]+)", row["body"]).group(1)
        for row in response.json()
        if f"flow={flow}" in row["body"]
    )


def test_account_lifecycle_and_session_revocation(business):
    client, _, _ = business
    email, password = "owner@example.com", "a-long-test-password"
    payload = dict(email=email, password=password, merchant_name="Independent shop")
    assert client.post("/api/v1/auth/register", json=payload).status_code == 202
    assert (
        client.post("/api/v1/auth/login", json=dict(email=email, password=password)).status_code
        == 401
    )
    token = token_from_inbox(client, email, "verify")
    assert client.post("/api/v1/auth/verify", json={"token": token}).status_code == 200
    assert client.post("/api/v1/auth/verify", json={"token": token}).status_code == 422
    login = client.post("/api/v1/auth/login", json=dict(email=email, password=password))
    assert login.status_code == 200 and login.json()["is_demo"] is False
    assert client.get("/api/v1/session").status_code == 200
    assert client.post("/api/v1/auth/forgot-password", json={"email": email}).status_code == 202
    reset = token_from_inbox(client, email, "reset")
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            json=dict(token=reset, password="different-long-password"),
        ).status_code
        == 200
    )
    assert client.get("/api/v1/session").status_code == 401
    assert (
        client.post("/api/v1/auth/login", json=dict(email=email, password=password)).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login", json=dict(email=email, password="different-long-password")
        ).status_code
        == 200
    )


def test_origin_and_local_inbox_boundaries(business):
    client, _, app = business
    assert (
        client.post(
            "/api/v1/auth/register",
            json=dict(email="a@example.com", password="a-long-password", merchant_name="Shop"),
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    app.state.settings.demo_enabled = False
    assert (
        client.get("/api/v1/auth/dev-inbox", params={"email": "a@example.com"}).status_code == 404
    )


def test_credit_partial_repayment_reversal_and_customer_scope(business):
    client, _, _ = business
    owner = customer(client)
    other = customer(client, email="other@example.com")
    past = (datetime.now(UTC) - timedelta(days=2)).date().isoformat()
    charge = dict(request_key="charge-1", amount_paise=10000, due_date=past)
    result = client.post(f"/api/v1/credit/{owner['id']}/charges", json=charge)
    assert result.status_code == 200, result.text
    event = result.json()["events"][0]
    repay = dict(request_key="repay-1", amount_paise=3000)
    ledger = client.post(f"/api/v1/credit/{owner['id']}/repayments", json=repay).json()
    assert ledger["balance_paise"] == ledger["overdue_paise"] == 7000
    assert client.post(f"/api/v1/credit/{owner['id']}/repayments", json=repay).json() == ledger
    assert (
        client.post(
            f"/api/v1/credit/{owner['id']}/repayments", json=repay | {"amount_paise": 4000}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/credit/events/{event['id']}/reverse",
            json=dict(request_key="bad-reverse", note="Correction"),
        ).status_code
        == 409
    )
    client.post(f"/api/v1/customers/{owner['id']}/portal-link")
    token = token_from_inbox(client, owner["email"], "portal")
    auth = {"Authorization": "Bearer " + token}
    assert client.get("/api/v1/portal", headers=auth).json()["balance_paise"] == 7000
    decision = client.post(
        "/api/v1/portal/acknowledge",
        headers=auth,
        json=dict(event_id=event["id"], decision="ACKNOWLEDGED"),
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["events"][0]["acknowledgement"] == "ACKNOWLEDGED"
    client.post(f"/api/v1/customers/{other['id']}/portal-link")
    other_token = token_from_inbox(client, other["email"], "portal")
    assert (
        client.post(
            "/api/v1/portal/acknowledge",
            headers={"Authorization": "Bearer " + other_token},
            json=dict(event_id=event["id"], decision="DISPUTED"),
        ).status_code
        == 404
    )
    payment = next(row for row in ledger["events"] if row["kind"] == "REPAYMENT")
    assert (
        client.post(
            f"/api/v1/credit/events/{payment['id']}/reverse",
            json=dict(request_key="reverse-repay", note="Correction"),
        ).json()["balance_paise"]
        == 10000
    )
    assert (
        client.post(
            f"/api/v1/credit/events/{event['id']}/reverse",
            json=dict(request_key="reverse-charge", note="Correction"),
        ).json()["balance_paise"]
        == 0
    )


def test_sales_snapshots_loyalty_and_void(business, database):
    client, _, _ = business
    item, person = product(client), customer(client)
    policy = dict(
        enabled=True,
        earning_spend_paise=10000,
        earning_points=1,
        point_value_paise=100,
        minimum_margin_bps=2000,
    )
    assert client.post("/api/v1/loyalty/settings", json=policy).status_code == 200
    payload = dict(
        request_key="sale-1",
        customer_id=person["id"],
        lines=[dict(product_id=item["id"], quantity=1)],
    )
    sale = client.post("/api/v1/sales", json=payload)
    assert sale.status_code == 201, sale.text
    assert sale.json()["profit_paise"] == 20000
    assert client.post("/api/v1/sales", json=payload).json() == sale.json()
    assert client.get(f"/api/v1/loyalty/{person['id']}").json()["available_points"] == 4
    changed = {key: value for key, value in item.items() if key != "id"} | {
        "unit_cost_paise": 30000,
        "stock_quantity": 19,
    }
    assert client.post(f"/api/v1/products/{item['id']}", json=changed).status_code == 200
    assert client.get("/api/v1/sales").json()["items"][0]["profit_paise"] == 20000
    with Session(database) as db:
        line = db.scalar(select(SaleLine))
        assert line.unit_cost_paise == 20000
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE sale_lines SET unit_cost_paise=1"))
            db.commit()
    result = client.post(
        f"/api/v1/sales/{sale.json()['id']}/void", json=dict(request_key="void-1", note="Returned")
    )
    assert result.status_code == 200, result.text
    assert result.json()["profit_paise"] is None
    assert client.get(f"/api/v1/loyalty/{person['id']}").json()["balance_points"] == 0
    assert client.get("/api/v1/transactions").json()["items"][0]["status"] == "REFUNDED"


def test_offer_economics_and_bounded_redemption(business):
    client, _, _ = business
    item = product(client, unit_cost_paise=32000)
    basket = dict(
        lines=[dict(product_id=item["id"], quantity=1)],
        rule=dict(type="FIXED", discount_paise=5000),
        minimum_margin_bps=2000,
    )
    quote = client.post("/api/v1/offers/evaluate", json=basket)
    assert quote.status_code == 200, quote.text
    assert quote.json()["eligible"] is False
    assert quote.json()["profit_paise"] == 3000
    basket["rule"]["discount_paise"] = 0
    now = datetime.now(UTC)
    payload = basket | dict(
        name="Reviewed offer",
        budget_cap_paise=0,
        max_redemptions=1,
        starts_at=(now - timedelta(minutes=1)).isoformat(),
        ends_at=(now + timedelta(days=1)).isoformat(),
    )
    offer = client.post("/api/v1/offers", json=payload)
    assert offer.status_code == 201, offer.text
    oid = offer.json()["id"]
    assert client.post(f"/api/v1/offers/{oid}/activate").status_code == 409
    assert client.post(f"/api/v1/offers/{oid}/approve").status_code == 200
    assert client.post(f"/api/v1/offers/{oid}/activate").status_code == 200
    sale = dict(request_key="offer-sale", lines=basket["lines"], offer_id=oid)
    assert client.post("/api/v1/sales", json=sale).status_code == 201
    assert (
        client.post("/api/v1/sales", json=sale | {"request_key": "offer-sale-2"}).status_code == 409
    )
    unknown = product(client, unit_cost_paise=None)
    assert (
        client.post(
            "/api/v1/offers/evaluate",
            json=basket | {"lines": [dict(product_id=unknown["id"], quantity=1)]},
        ).json()["cost_paise"]
        is None
    )


def test_last_stock_is_serialized(business, database):
    client, actor, _ = business
    item = product(client, stock_quantity=1)

    def attempt(index):
        with Session(database, expire_on_commit=False) as db:
            try:
                return record_sale(
                    db,
                    actor,
                    SaleCreate(
                        request_key=f"race-{index}", lines=[dict(product_id=item["id"], quantity=1)]
                    ),
                ).status
            except Exception as error:
                return getattr(error, "code", type(error).__name__)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, range(2)))
    assert sorted(outcomes) == ["INSUFFICIENT_STOCK", "RECORDED"]


def test_consent_single_use_email_change_and_tenant_scope(business, database):
    client, _, _ = business
    person = customer(client, request_marketing_consent=True)
    assert person["marketing_opt_in"] is False
    token = token_from_inbox(client, person["email"], "consent")
    assert (
        client.post("/api/v1/public/consent", json=dict(token=token, decision="OPT_IN")).status_code
        == 200
    )
    assert (
        client.post("/api/v1/public/consent", json=dict(token=token, decision="OPT_IN")).status_code
        == 401
    )
    changed = client.post(
        f"/api/v1/customers/{person['id']}",
        json=dict(name=person["name"], email="changed@example.com"),
    )
    assert changed.status_code == 200 and changed.json()["marketing_opt_in"] is False
    from conftest import add_actor

    other, _, _ = add_actor(database, "Other merchant")
    with Session(database) as db:
        foreign = Product(
            merchant_id=other.merchant_id,
            sku="foreign",
            name="Foreign",
            selling_price_paise=100,
            active=True,
        )
        db.add(foreign)
        db.flush()
        foreign_id = str(foreign.id)
        db.commit()
    assert (
        client.post(
            "/api/v1/sales",
            json=dict(request_key="cross-tenant", lines=[dict(product_id=foreign_id, quantity=1)]),
        ).status_code
        == 404
    )
