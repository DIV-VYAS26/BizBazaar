from datetime import UTC, datetime

from sqlalchemy import select

from app.core.errors import ApiError
from app.core.security import lock_merchant
from app.db.commerce import (
    CreditEvent,
    Customer,
    LoyaltyEvent,
    LoyaltyPolicy,
    Product,
    ProfitOffer,
    Sale,
    SaleLine,
)
from app.db.models import Transaction
from app.schemas.commerce import OfferEvaluate, SaleView
from app.services.business import owned, remember, replay
from app.services.catalog import basket_products
from app.services.credit import append_credit, reverse_event
from app.services.loyalty import points_balance
from app.services.metadata import invalidate_coverage
from app.services.offers import quote_products
from app.services.transactions import atomic, audit


@atomic
def record_sale(db, actor, payload):
    lock_merchant(db, actor)
    previous = replay(db, actor, "SALE", payload.request_key, payload)
    if previous is not None:
        return SaleView.model_validate(previous)
    if payload.customer_id:
        owned(db, Customer, actor.merchant_id, payload.customer_id)
    products = basket_products(db, actor.merchant_id, payload.lines)
    subtotal = sum(product.selling_price_paise * quantity for product, quantity in products)
    cost = (
        sum(product.unit_cost_paise * quantity for product, quantity in products)
        if all(product.unit_cost_paise is not None for product, _ in products)
        else None
    )
    for product, quantity in products:
        if product.stock_quantity is not None and product.stock_quantity < quantity:
            raise ApiError(409, "INSUFFICIENT_STOCK", "Basket exceeds recorded stock")
    discount, offer = 0, None
    if payload.offer_id:
        offer = owned(db, ProfitOffer, actor.merchant_id, payload.offer_id, lock=True)
        now = datetime.now(UTC)
        if offer.status != "ACTIVE" or not offer.starts_at <= now < offer.ends_at:
            raise ApiError(409, "OFFER_INACTIVE", "Selected offer is not active")
        specification = OfferEvaluate.model_validate(offer.specification)
        expected = {str(line.product_id): line.quantity for line in specification.lines}
        actual = {str(line.product_id): line.quantity for line in payload.lines}
        quote = quote_products(products, specification.rule, specification.minimum_margin_bps)
        if (
            expected != actual
            or quote.product_versions != offer.product_versions
            or not quote.eligible
        ):
            raise ApiError(
                409,
                "OFFER_MISMATCH",
                "Basket or product economics no longer match the approved offer",
            )
        discount = quote.discount_paise
        if (
            offer.redemption_count >= offer.max_redemptions
            or offer.discount_spent_paise + discount > offer.budget_cap_paise
        ):
            raise ApiError(409, "OFFER_BUDGET", "Offer redemption limit or budget is exhausted")
    policy = db.get(LoyaltyPolicy, actor.merchant_id)
    if payload.redeem_points:
        if not policy or not policy.enabled or not payload.customer_id:
            raise ApiError(
                409,
                "LOYALTY_UNAVAILABLE",
                "Loyalty redemption requires an enabled policy and customer",
            )
        if points_balance(db, actor.merchant_id, payload.customer_id) < payload.redeem_points:
            raise ApiError(409, "INSUFFICIENT_POINTS", "Customer has insufficient available points")
        discount += payload.redeem_points * policy.point_value_paise
        revenue = subtotal - discount
        required_margin = max(
            policy.minimum_margin_bps, specification.minimum_margin_bps if offer else 0
        )
        if cost is None or revenue <= 0 or (revenue - cost) * 10000 < required_margin * revenue:
            raise ApiError(
                409,
                "UNSAFE_REDEMPTION",
                "Combined discounts violate known-cost or margin requirements",
            )
    total = subtotal - discount
    if total <= 0:
        raise ApiError(422, "INVALID_TOTAL", "Sale must retain a positive total")
    sale = Sale(
        merchant_id=actor.merchant_id,
        customer_id=payload.customer_id,
        offer_id=payload.offer_id,
        payment_method=payload.payment_method,
        subtotal_paise=subtotal,
        discount_paise=discount,
        total_paise=total,
        cost_paise=cost,
        redeemed_points=payload.redeem_points,
    )
    db.add(sale)
    db.flush()
    for product, quantity in products:
        if product.stock_quantity is not None:
            product.stock_quantity -= quantity
        db.add(
            SaleLine(
                merchant_id=actor.merchant_id,
                sale_id=sale.id,
                product_id=product.id,
                product_name=product.name,
                quantity=quantity,
                unit_price_paise=product.selling_price_paise,
                unit_cost_paise=product.unit_cost_paise,
            )
        )
    if payload.payment_method == "CREDIT":
        event = append_credit(
            db,
            actor,
            payload.customer_id,
            "CHARGE",
            total,
            payload.due_date,
            "Credit sale " + str(sale.id),
        )
        sale.credit_event_id = event.id
    else:
        transaction = Transaction(
            merchant_id=actor.merchant_id,
            transaction_id="SALE_" + sale.id.hex,
            amount_paise=total,
            timestamp=datetime.now(UTC),
            status="SUCCESS",
            source="MANUAL",
            is_simulated=False,
        )
        db.add(transaction)
        db.flush()
        sale.transaction_pk = transaction.id
        invalidate_coverage(db, actor, transaction.timestamp, is_simulated=False)
    if offer:
        offer.redemption_count += 1
        offer.discount_spent_paise += quote.discount_paise
    if policy and policy.enabled and payload.customer_id and payload.payment_method != "CREDIT":
        earned = (total // policy.earning_spend_paise) * policy.earning_points
        if earned > 1_000_000:
            raise ApiError(
                422,
                "LOYALTY_LIMIT",
                "Configured policy exceeds the supported per-sale points award",
            )
        for kind, points in [("EARN", earned), ("REDEEM", -payload.redeem_points)]:
            if points:
                db.add(
                    LoyaltyEvent(
                        merchant_id=actor.merchant_id,
                        customer_id=payload.customer_id,
                        sale_id=sale.id,
                        kind=kind,
                        points_delta=points,
                        source_key=f"{kind}:{sale.id}",
                    )
                )
    audit(
        db,
        actor,
        "SALE_RECORDED",
        sale.id,
        {"total_paise": total, "payment_method": payload.payment_method},
    )
    db.flush()
    result = SaleView.model_validate(sale)
    remember(db, actor, "SALE", payload.request_key, payload, result)
    return result


@atomic
def void_sale(db, actor, sale_id, payload):
    lock_merchant(db, actor)
    scope = "VOID:" + str(sale_id)
    previous = replay(db, actor, scope, payload.request_key, payload)
    if previous is not None:
        return SaleView.model_validate(previous)
    sale = owned(db, Sale, actor.merchant_id, sale_id, lock=True)
    if sale.status == "VOIDED":
        raise ApiError(409, "ALREADY_VOIDED", "Sale was already voided")
    if sale.credit_event_id:
        event = owned(db, CreditEvent, actor.merchant_id, sale.credit_event_id)
        reverse_event(db, actor, event, payload.note)
    if sale.transaction_pk:
        transaction = owned(db, Transaction, actor.merchant_id, sale.transaction_pk)
        transaction.status = "REFUNDED"
    lines = db.scalars(
        select(SaleLine).where(
            SaleLine.merchant_id == actor.merchant_id, SaleLine.sale_id == sale.id
        )
    ).all()
    for line in lines:
        product = owned(db, Product, actor.merchant_id, line.product_id)
        if product.stock_quantity is not None:
            product.stock_quantity += line.quantity
    events = db.scalars(
        select(LoyaltyEvent).where(
            LoyaltyEvent.merchant_id == actor.merchant_id, LoyaltyEvent.sale_id == sale.id
        )
    ).all()
    for event in events:
        db.add(
            LoyaltyEvent(
                merchant_id=actor.merchant_id,
                customer_id=event.customer_id,
                sale_id=sale.id,
                points_delta=-event.points_delta,
                kind="REVERSAL",
                source_key="REVERSE:" + str(event.id),
            )
        )
    # Do not restore promotion budget: the issued discount opportunity was consumed.
    sale.status = "VOIDED"
    audit(db, actor, "SALE_VOIDED", sale.id, {"reason": payload.note})
    db.flush()
    result = SaleView.model_validate(sale)
    remember(db, actor, scope, payload.request_key, payload, result)
    return result
