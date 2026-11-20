import json

from sqlalchemy import select

from app.core.errors import ApiError
from app.core.security import digest
from app.db.commerce import BusinessRequest


def owned(db, model, merchant_id, resource_id, *, lock=False):
    query = select(model).where(model.id == resource_id, model.merchant_id == merchant_id)
    if lock:
        query = query.with_for_update()
    row = db.scalar(query.execution_options(populate_existing=True))
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Record not found")
    return row


def fingerprint(payload):
    data = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
    return digest(json.dumps(data, sort_keys=True, separators=(",", ":")))


def replay(db, actor, scope, key, payload):
    previous = db.scalar(
        select(BusinessRequest).where(
            BusinessRequest.merchant_id == actor.merchant_id, BusinessRequest.request_key == key
        )
    )
    if previous:
        if previous.scope != scope or previous.fingerprint != fingerprint(payload):
            raise ApiError(
                409, "REQUEST_CONFLICT", "Request key was already used for a different action"
            )
        return previous.result
    return None


def remember(db, actor, scope, key, payload, result):
    result = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
    db.add(
        BusinessRequest(
            merchant_id=actor.merchant_id,
            scope=scope,
            request_key=key,
            fingerprint=fingerprint(payload),
            result=result,
        )
    )
    db.flush()
    return result
