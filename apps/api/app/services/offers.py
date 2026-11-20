from datetime import UTC, datetime

from app.core.errors import ApiError
from app.core.security import lock_merchant
from app.db.commerce import ProfitOffer
from app.schemas.commerce import OfferEvaluate, OfferQuote, OfferView
from app.services.business import owned
from app.services.catalog import basket_products
from app.services.transactions import atomic, audit


def quote_products(products, rule, minimum_margin_bps):
    subtotal = sum(product.selling_price_paise * quantity for product, quantity in products)
    known_cost = all(product.unit_cost_paise is not None for product, _ in products)
    cost = (
        sum(product.unit_cost_paise * quantity for product, quantity in products)
        if known_cost
        else None
    )
    discount, violations = 0, []
    if rule.type == "FIXED":
        discount = rule.discount_paise
    elif rule.type == "PERCENT":
        discount = (2 * subtotal * rule.percentage_bps + 10000) // 20000
    elif rule.type == "BOGO":
        if len(products) != 1 or products[0][1] < 2:
            violations.append("BOGO requires at least two units of one product")
        else:
            product, quantity = products[0]
            discount = (quantity // 2) * product.selling_price_paise
    elif rule.type == "BUNDLE":
        discount = subtotal - rule.bundle_price_paise
        if discount < 0:
            violations.append("Bundle price exceeds the ordinary basket price")
    elif rule.type == "THRESHOLD":
        if subtotal < rule.threshold_paise:
            violations.append("Basket does not reach the purchase threshold")
        else:
            discount = rule.discount_paise
    if discount < 0 or discount >= subtotal:
        violations.append("Discount must leave positive revenue")
    revenue = subtotal - discount
    profit = revenue - cost if cost is not None else None
    margin = (profit * 10000) // revenue if profit is not None and revenue > 0 else None
    if cost is None:
        violations.append("Product costs are missing; profit and margin are unknown")
    elif revenue <= 0 or (revenue - cost) * 10000 < minimum_margin_bps * revenue:
        violations.append("Offer violates the merchant's minimum gross margin")
    return OfferQuote(
        subtotal_paise=subtotal,
        discount_paise=discount,
        revenue_paise=revenue,
        cost_paise=cost,
        profit_paise=profit,
        margin_bps=margin,
        eligible=not violations,
        violations=violations,
        product_versions={str(product.id): product.version for product, _ in products},
    )


def evaluate_offer(db, actor, payload):
    products = basket_products(db, actor.merchant_id, payload.lines)
    return quote_products(products, payload.rule, payload.minimum_margin_bps)


@atomic
def create_offer(db, actor, payload):
    lock_merchant(db, actor)
    quote = evaluate_offer(db, actor, payload)
    if not quote.eligible:
        raise ApiError(422, "UNSAFE_OFFER", "Offer cannot be published", quote.violations)
    if quote.discount_paise * payload.max_redemptions > payload.budget_cap_paise:
        raise ApiError(422, "OFFER_BUDGET", "Budget must cover the configured maximum redemptions")
    if payload.ends_at <= datetime.now(UTC):
        raise ApiError(422, "INVALID_DATES", "Offer end must be in the future")
    row = ProfitOffer(
        merchant_id=actor.merchant_id,
        name=payload.name,
        specification=OfferEvaluate(
            **payload.model_dump(include={"lines", "rule", "minimum_margin_bps"})
        ).model_dump(mode="json"),
        quote=quote.model_dump(mode="json"),
        product_versions=quote.product_versions,
        budget_cap_paise=payload.budget_cap_paise,
        max_redemptions=payload.max_redemptions,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db.add(row)
    db.flush()
    audit(db, actor, "PROFIT_OFFER_CREATED", row.id)
    return OfferView.model_validate(row)


@atomic
def transition_offer(db, actor, offer_id, action):
    lock_merchant(db, actor)
    row = owned(db, ProfitOffer, actor.merchant_id, offer_id, lock=True)
    expected, target = {
        "approve": ("DRAFT", "APPROVED"),
        "activate": ("APPROVED", "ACTIVE"),
        "complete": ("ACTIVE", "COMPLETED"),
    }[action]
    if row.status == target:
        return OfferView.model_validate(row)
    if row.status != expected:
        raise ApiError(409, "INVALID_STATE", "Offer cannot perform this transition")
    if action != "complete":
        payload = OfferEvaluate.model_validate(row.specification)
        current = evaluate_offer(db, actor, payload)
        if not current.eligible or current.product_versions != row.product_versions:
            raise ApiError(
                409, "STALE_OFFER", "Product economics changed; create and review a fresh offer"
            )
        if datetime.now(UTC) >= row.ends_at:
            raise ApiError(409, "OFFER_EXPIRED", "Offer has expired")
    if action == "activate" and not row.starts_at <= datetime.now(UTC) < row.ends_at:
        raise ApiError(409, "OUTSIDE_WINDOW", "Offer is outside its activation window")
    row.status = target
    audit(db, actor, "PROFIT_OFFER_" + target, row.id)
    db.flush()
    return OfferView.model_validate(row)
