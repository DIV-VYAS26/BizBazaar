from app.core.errors import ApiError
from app.core.security import lock_merchant
from app.db.commerce import Product
from app.schemas.commerce import ProductView
from app.services.business import owned
from app.services.transactions import atomic, audit


@atomic
def create_product(db, actor, payload):
    lock_merchant(db, actor)
    row = Product(merchant_id=actor.merchant_id, **payload.model_dump())
    db.add(row)
    db.flush()
    audit(db, actor, "PRODUCT_CREATED", row.id)
    return ProductView.model_validate(row)


@atomic
def update_product(db, actor, product_id, payload):
    lock_merchant(db, actor)
    row = owned(db, Product, actor.merchant_id, product_id, lock=True)
    if row.version != payload.version:
        raise ApiError(409, "STALE_PRODUCT", "Product changed; reload before updating")
    for key, value in payload.model_dump(exclude={"version"}).items():
        setattr(row, key, value)
    row.version += 1
    audit(db, actor, "PRODUCT_UPDATED", row.id, {"version": row.version})
    db.flush()
    return ProductView.model_validate(row)


def basket_products(db, merchant_id, lines):
    result = []
    for line in lines:
        product = owned(db, Product, merchant_id, line.product_id)
        if not product.active:
            raise ApiError(409, "INACTIVE_PRODUCT", "Basket contains an inactive product")
        result.append((product, line.quantity))
    total = sum(product.selling_price_paise * quantity for product, quantity in result)
    if total <= 0 or total > 1_000_000_000_000:
        raise ApiError(422, "INVALID_TOTAL", "Basket exceeds the supported sale amount")
    return result
