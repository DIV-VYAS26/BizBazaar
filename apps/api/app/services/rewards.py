import hashlib
import json
from datetime import UTC

from sqlalchemy import select

from app.core.errors import ApiError
from app.core.security import lock_merchant
from app.db.models import Campaign, PaymentEvent, ProcessedTransaction, Reward, Transaction
from app.schemas.api import PaymentDecision, TransactionView
from app.services.campaigns import now_utc, reconcile_expiry
from app.services.metadata import invalidate_coverage
from app.services.transactions import atomic, audit


def fingerprint(payload):
    # UTC normalization avoids treating equivalent timestamp offsets as different requests.
    data = payload.model_dump(mode="json")
    data["timestamp"] = payload.timestamp.astimezone(UTC).isoformat()
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


@atomic
def simulate_payment(db, actor, payload):
    lock_merchant(db, actor)
    # Merchant serialization means a same-merchant race waits until the first commit.
    # The constraints independently enforce uniqueness if another writer is added later.
    previous = db.scalar(
        select(PaymentEvent).where(
            PaymentEvent.merchant_id == actor.merchant_id,
            PaymentEvent.event_id == payload.event_id,
        )
    )
    request_hash = fingerprint(payload)
    if previous:
        if previous.fingerprint != request_hash:
            raise ApiError(409, "EVENT_CONFLICT", "Event ID was used with a different payload")
        return PaymentDecision.model_validate(previous.decision)
    existing = db.scalar(
        select(Transaction.id).where(
            Transaction.merchant_id == actor.merchant_id,
            Transaction.transaction_id == payload.transaction_id,
        )
    )
    if existing:
        raise ApiError(409, "TRANSACTION_CONFLICT", "Transaction ID has already been recorded")

    now = now_utc()
    reconcile_expiry(db, actor, now)
    campaign = db.scalar(
        select(Campaign)
        .where(Campaign.merchant_id == actor.merchant_id, Campaign.status == "ACTIVE")
        .with_for_update()
    )
    transaction = Transaction(
        merchant_id=actor.merchant_id,
        transaction_id=payload.transaction_id,
        amount_paise=payload.amount_paise,
        timestamp=payload.timestamp,
        status=payload.status.value,
        source="SIMULATOR",
        is_simulated=True,
    )
    db.add(transaction)
    db.flush()
    invalidate_coverage(db, actor, transaction.timestamp, is_simulated=True)
    decision, reward_id, sequence = "CAMPAIGN_INACTIVE", None, None
    if campaign and campaign.starts_at <= now < campaign.ends_at:
        decision = "NOT_ELIGIBLE"
        if payload.status.value == "SUCCESS":
            prior = campaign.cumulative_paise
            campaign.eligible_count += 1
            campaign.cumulative_paise += payload.amount_paise
            sequence = campaign.eligible_count
            if campaign.type == "NTH_PAYMENT":
                qualifies = sequence % campaign.rule_parameters["n"] == 0
            else:
                qualifies = (
                    not campaign.threshold_awarded
                    and prior
                    < campaign.rule_parameters["threshold_paise"]
                    <= campaign.cumulative_paise
                )
            if qualifies:
                remaining = (
                    campaign.budget_cap_paise - campaign.consumed_paise - campaign.reserved_paise
                )
                if remaining >= campaign.reward_cost_paise:
                    reward = Reward(
                        merchant_id=actor.merchant_id,
                        campaign_id=campaign.id,
                        transaction_pk=transaction.id,
                        cost_paise=campaign.reward_cost_paise,
                    )
                    db.add(reward)
                    db.flush()
                    reward_id = reward.id
                    campaign.consumed_paise += reward.cost_paise
                    if campaign.type == "COLLECTION_THRESHOLD":
                        campaign.threshold_awarded = True
                    decision = "ISSUED"
                else:
                    decision = "SKIPPED_BUDGET"
    result = PaymentDecision(
        event_id=payload.event_id,
        transaction_id=payload.transaction_id,
        campaign_id=campaign.id if campaign else None,
        decision=decision,
        reward_id=reward_id,
        acceptance_sequence=sequence,
        reward_cost_paise=campaign.reward_cost_paise if reward_id else 0,
        remaining_budget_paise=(
            campaign.budget_cap_paise - campaign.consumed_paise - campaign.reserved_paise
        )
        if campaign
        else None,
        eligible_count=campaign.eligible_count if campaign else None,
    )
    db.add(
        ProcessedTransaction(
            merchant_id=actor.merchant_id,
            transaction_pk=transaction.id,
            campaign_id=campaign.id if campaign else None,
            acceptance_sequence=sequence,
        )
    )
    db.add(
        PaymentEvent(
            merchant_id=actor.merchant_id,
            event_id=payload.event_id,
            transaction_pk=transaction.id,
            fingerprint=request_hash,
            decision=result.model_dump(mode="json"),
        )
    )
    audit(
        db,
        actor,
        "PAYMENT_SIMULATED",
        transaction.id,
        {"decision": decision, "campaign_id": str(campaign.id) if campaign else None},
    )
    db.flush()
    return result


@atomic
def simulate_refund(db, actor, transaction_id):
    lock_merchant(db, actor)
    row = db.scalar(
        select(Transaction)
        .where(Transaction.id == transaction_id, Transaction.merchant_id == actor.merchant_id)
        .with_for_update()
    )
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Transaction not found")
    if row.source != "SIMULATOR":
        raise ApiError(409, "NOT_SIMULATED", "Only simulator transactions can be updated")
    if row.status == "REFUNDED":
        return TransactionView.model_validate(row)
    if row.status != "SUCCESS":
        raise ApiError(409, "INVALID_STATE", "Only successful transactions can be fully refunded")
    row.status = "REFUNDED"
    audit(db, actor, "REFUND_SIMULATED", row.id, {"from": "SUCCESS", "to": "REFUNDED"})
    db.flush()
    return TransactionView.model_validate(row)
