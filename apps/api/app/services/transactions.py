from functools import wraps

from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.errors import ApiError
from app.db.models import AuditLog


def atomic(function):
    """Commit business and audit writes together; retry only aborted transient transactions."""

    @wraps(function)
    def wrapped(db, actor, *args, **kwargs):
        for attempt in range(3):
            try:
                result = function(db, actor, *args, **kwargs)
                db.commit()
                return result
            except DBAPIError as exc:
                db.rollback()
                code = getattr(exc.orig, "sqlstate", None)
                if code in {"40001", "40P01"} and attempt < 2:
                    continue
                if code in {"55P03", "57014", "40001", "40P01"}:
                    raise ApiError(
                        503, "DATABASE_BUSY", "Request could not complete; retry safely"
                    ) from None
                if isinstance(exc, IntegrityError):
                    raise ApiError(
                        409, "CONFLICT", "Request conflicts with existing data"
                    ) from None
                raise
            except Exception:
                db.rollback()
                raise

    return wrapped


def audit(db, actor, action, resource_id, changes=None):
    db.add(
        AuditLog(
            merchant_id=actor.merchant_id,
            actor_id=actor.session_id,
            action=action,
            resource_id=str(resource_id),
            changes=changes or {},
        )
    )


def system_audit(db, merchant_id, action, resource_id, changes=None, actor_type="SYSTEM"):
    db.add(
        AuditLog(
            merchant_id=merchant_id,
            actor_id=None,
            actor_type=actor_type,
            action=action,
            resource_id=str(resource_id),
            changes=changes or {},
        )
    )
