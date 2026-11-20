from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.core.errors import ApiError
from app.core.security import lock_merchant
from app.db.commerce import CreditAccount, CreditAcknowledgement, CreditEvent, Customer, Sale
from app.db.models import Merchant, Transaction
from app.schemas.commerce import CreditEventView, CreditLedgerView, CustomerView
from app.services.business import owned, remember, replay
from app.services.metadata import invalidate_coverage
from app.services.transactions import atomic, audit


def account_for(db, merchant_id, customer_id, create=False):
    owned(db, Customer, merchant_id, customer_id)
    account = db.scalar(
        select(CreditAccount).where(
            CreditAccount.merchant_id == merchant_id, CreditAccount.customer_id == customer_id
        )
    )
    if account is None and create:
        account = CreditAccount(merchant_id=merchant_id, customer_id=customer_id)
        db.add(account)
        db.flush()
    return account


def account_balance(db, merchant_id, account_id):
    return int(
        db.scalar(
            select(func.coalesce(func.sum(CreditEvent.delta_paise), 0)).where(
                CreditEvent.merchant_id == merchant_id, CreditEvent.account_id == account_id
            )
        )
        or 0
    )


def append_credit(db, actor, customer_id, kind, amount, due_date=None, note=""):
    account = account_for(db, actor.merchant_id, customer_id, create=True)
    balance = account_balance(db, actor.merchant_id, account.id)
    if kind == "REPAYMENT" and amount > balance:
        raise ApiError(409, "OVERPAYMENT", "Repayment exceeds the outstanding balance")
    row = CreditEvent(
        merchant_id=actor.merchant_id,
        account_id=account.id,
        kind=kind,
        delta_paise=amount if kind == "CHARGE" else -amount,
        due_date=due_date,
        note=note,
        actor_id=actor.session_id,
    )
    db.add(row)
    db.flush()
    if kind == "REPAYMENT":
        record = Transaction(
            merchant_id=actor.merchant_id,
            transaction_id="CREDIT_" + row.id.hex,
            amount_paise=amount,
            timestamp=datetime.now(UTC),
            status="SUCCESS",
            source="MANUAL",
            is_simulated=False,
        )
        db.add(record)
        invalidate_coverage(db, actor, record.timestamp, is_simulated=False)
    audit(db, actor, "CREDIT_" + kind, row.id, {"amount_paise": amount})
    db.flush()
    return row


def ledger(db, merchant_id, customer_id):
    customer = owned(db, Customer, merchant_id, customer_id)
    account = account_for(db, merchant_id, customer_id)
    rows = (
        db.scalars(
            select(CreditEvent)
            .where(CreditEvent.merchant_id == merchant_id, CreditEvent.account_id == account.id)
            .order_by(CreditEvent.created_at, CreditEvent.id)
        ).all()
        if account
        else []
    )
    acknowledgements = dict(
        db.execute(
            select(CreditAcknowledgement.event_id, CreditAcknowledgement.decision).where(
                CreditAcknowledgement.merchant_id == merchant_id,
                CreditAcknowledgement.customer_id == customer_id,
            )
        ).all()
    )
    reversed_ids = {row.reverses_id for row in rows if row.kind == "REVERSAL"}
    active = [row for row in rows if row.kind != "REVERSAL" and row.id not in reversed_ids]
    repayments = sum(-row.delta_paise for row in active if row.kind == "REPAYMENT")
    today = datetime.now(UTC).astimezone(ZoneInfo(db.get(Merchant, merchant_id).timezone)).date()
    overdue = 0
    charges = sorted(
        [row for row in active if row.kind == "CHARGE"],
        key=lambda row: (row.due_date or date.max, row.created_at, str(row.id)),
    )
    for charge in charges:
        applied = min(repayments, charge.delta_paise)
        repayments -= applied
        if charge.due_date and charge.due_date < today:
            overdue += charge.delta_paise - applied
    views = [
        CreditEventView.model_validate(row).model_copy(
            update={
                "acknowledgement": "REVERSED"
                if row.id in reversed_ids
                else (
                    acknowledgements.get(row.id, "PENDING")
                    if row.kind == "CHARGE"
                    else "NOT_REQUIRED"
                )
            }
        )
        for row in rows
    ]
    return CreditLedgerView(
        customer=CustomerView.model_validate(customer),
        balance_paise=sum(row.delta_paise for row in rows),
        overdue_paise=overdue,
        events=views,
    )


@atomic
def post_credit(db, actor, customer_id, payload, kind):
    lock_merchant(db, actor)
    scope = kind + ":" + str(customer_id)
    previous = replay(db, actor, scope, payload.request_key, payload)
    if previous is not None:
        return CreditLedgerView.model_validate(previous)
    if kind == "CHARGE" and payload.due_date is None:
        raise ApiError(422, "DUE_DATE_REQUIRED", "Credit charges require a due date")
    append_credit(
        db, actor, customer_id, kind, payload.amount_paise, payload.due_date, payload.note
    )
    result = ledger(db, actor.merchant_id, customer_id)
    remember(db, actor, scope, payload.request_key, payload, result)
    return result


def reverse_event(db, actor, event, note):
    if event.kind == "REVERSAL" or db.scalar(
        select(CreditEvent.id).where(CreditEvent.reverses_id == event.id)
    ):
        raise ApiError(409, "ALREADY_REVERSED", "Event cannot be reversed again")
    balance = account_balance(db, actor.merchant_id, event.account_id)
    if balance - event.delta_paise < 0:
        raise ApiError(
            409, "NEGATIVE_BALANCE", "Reverse the related repayments before removing this charge"
        )
    reversal = CreditEvent(
        merchant_id=actor.merchant_id,
        account_id=event.account_id,
        kind="REVERSAL",
        delta_paise=-event.delta_paise,
        reverses_id=event.id,
        actor_id=actor.session_id,
        note=note,
    )
    db.add(reversal)
    if event.kind == "REPAYMENT":
        transaction = db.scalar(
            select(Transaction).where(
                Transaction.merchant_id == actor.merchant_id,
                Transaction.transaction_id == "CREDIT_" + event.id.hex,
            )
        )
        if transaction:
            transaction.status = "REFUNDED"
    audit(db, actor, "CREDIT_REVERSED", event.id)
    db.flush()


@atomic
def reverse_credit(db, actor, event_id, payload):
    lock_merchant(db, actor)
    scope = "REVERSE:" + str(event_id)
    previous = replay(db, actor, scope, payload.request_key, payload)
    if previous is not None:
        return CreditLedgerView.model_validate(previous)
    event = owned(db, CreditEvent, actor.merchant_id, event_id)
    if db.scalar(
        select(Sale.id).where(
            Sale.merchant_id == actor.merchant_id,
            Sale.credit_event_id == event_id,
            Sale.status == "RECORDED",
        )
    ):
        raise ApiError(
            409,
            "USE_SALE_VOID",
            "Void the linked credit sale to reverse its charge and restore stock together",
        )
    account = owned(db, CreditAccount, actor.merchant_id, event.account_id)
    reverse_event(db, actor, event, payload.note)
    result = ledger(db, actor.merchant_id, account.customer_id)
    remember(db, actor, scope, payload.request_key, payload, result)
    return result
