import secrets
from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select, text

from app.core.errors import ApiError
from app.db.commerce import EmailOutbox
from app.routers.api import CurrentActor, Db
from app.schemas.api import MessageView
from app.services.worker import queue_due_reminders

router = APIRouter(tags=["operations"])


@router.get("/health/ready", response_model=MessageView)
def ready(request: Request, db: Db):
    try:
        db.execute(text("SELECT 1"))
        if request.app.state.settings.app_env == "production":
            unsafe = db.scalar(
                text("""SELECT rolsuper OR rolcreatedb OR rolcreaterole
              OR rolbypassrls OR pg_has_role(current_user, c.relowner, 'MEMBER')
              FROM pg_roles r CROSS JOIN pg_class c
              WHERE r.rolname=current_user AND c.oid='audit_logs'::regclass""")
            )
            if unsafe:
                raise ApiError(
                    503, "UNSAFE_DATABASE_ROLE", "Runtime database role is overprivileged"
                )
    except ApiError:
        raise
    except Exception:
        raise ApiError(503, "NOT_READY", "Database is unavailable") from None
    return MessageView(message="Ready")


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(request: Request, db: Db, authorization: Annotated[str | None, Header()] = None):
    configured = request.app.state.settings.metrics_token
    if not configured or not secrets.compare_digest(
        authorization or "", "Bearer " + configured.get_secret_value()
    ):
        raise ApiError(401, "UNAUTHENTICATED", "Metrics authentication required")
    pending = db.scalar(
        select(func.count())
        .select_from(EmailOutbox)
        .where(EmailOutbox.status.in_(["QUEUED", "RETRY", "SENDING"]))
    )
    failed = db.scalar(
        select(func.count()).select_from(EmailOutbox).where(EmailOutbox.status == "FAILED")
    )
    # No merchant IDs, email addresses, request URLs, amounts or tokens in labels.
    return (
        f"# TYPE bizbazaar_mail_pending gauge\nbizbazaar_mail_pending {pending}\n"
        f"# TYPE bizbazaar_mail_failed gauge\nbizbazaar_mail_failed {failed}\n"
    )


@router.post("/credit/reminders/queue", response_model=MessageView)
def reminders(request: Request, actor: CurrentActor, db: Db):
    count = queue_due_reminders(db, actor, request.app.state.settings)
    return MessageView(message=f"Queued {count} due reminders; delivery follows outbox settings")
