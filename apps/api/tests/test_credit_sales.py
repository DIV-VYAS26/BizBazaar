from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_commerce import customer, product

from app.db.commerce import CreditEvent


def test_credit_sale_void_reverses_stock_and_debt_together(business, database):
    client, _, _ = business
    person, item = customer(client), product(client)
    response = client.post(
        "/api/v1/sales",
        json={
            "request_key": "credit-sale",
            "customer_id": person["id"],
            "payment_method": "CREDIT",
            "due_date": "2026-01-01",
            "lines": [{"product_id": item["id"], "quantity": 1}],
        },
    )
    assert response.status_code == 201, response.text
    assert client.get("/api/v1/transactions").json()["total"] == 0
    ledger = client.get(f"/api/v1/credit/{person['id']}").json()
    assert ledger["balance_paise"] == 40000
    event_id = ledger["events"][0]["id"]
    reversal = {"request_key": "reverse-sale-charge", "note": "Test correction"}
    assert (
        client.post(f"/api/v1/credit/events/{event_id}/reverse", json=reversal).json()["error"][
            "code"
        ]
        == "USE_SALE_VOID"
    )
    with Session(database) as db:
        assert db.scalar(select(CreditEvent)).delta_paise == 40000
        try:
            db.execute(text("UPDATE credit_events SET delta_paise=1"))
            db.commit()
            raise AssertionError("Database allowed rewriting credit history")
        except DBAPIError:
            db.rollback()
    void = client.post(
        f"/api/v1/sales/{response.json()['id']}/void",
        json={"request_key": "void-credit-sale", "note": "Test return"},
    )
    assert void.status_code == 200
    assert client.get(f"/api/v1/credit/{person['id']}").json()["balance_paise"] == 0
    assert client.get("/api/v1/products").json()["items"][0]["stock_quantity"] == 20
