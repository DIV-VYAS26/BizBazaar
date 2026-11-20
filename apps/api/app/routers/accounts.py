from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    Actor,
    authenticate,
    digest,
    lock_merchant,
)
from app.db.commerce import EmailOutbox
from app.db.models import DemoSession
from app.db.session import get_db
from app.schemas.accounts import (
    AuthOptions,
    DevEmailView,
    EmailInput,
    LoginInput,
    PasswordResetInput,
    RegisterInput,
    TokenInput,
)
from app.schemas.api import MessageView, SessionView
from app.services import accounts
from app.services.mail import cipher
from app.services.transactions import audit

router = APIRouter(prefix="/auth", tags=["merchant accounts"])
Db = Annotated[Session, Depends(get_db)]
CurrentActor = Annotated[Actor, Depends(authenticate)]


def origin_guard(request):
    if request.headers.get("origin") not in request.app.state.settings.allowed_origins:
        raise ApiError(403, "ORIGIN_REJECTED", "Browser origin is not permitted")


def auth_limit(request, db, operation, email):
    origin_guard(request)
    accounts.enforce_auth_limit(
        db, operation, email, request.client.host if request.client else "unknown"
    )


def local_inbox_enabled(settings):
    return (
        settings.app_env in {"local", "test"}
        and settings.demo_enabled
        and settings.mail_delivery_mode == "outbox"
    )


@router.get("/options", response_model=AuthOptions)
def options(request: Request):
    settings = request.app.state.settings
    return AuthOptions(
        registration_enabled=settings.registration_enabled,
        local_inbox_enabled=local_inbox_enabled(settings),
        demo_enabled=settings.demo_enabled,
    )


@router.post("/register", response_model=MessageView, status_code=202)
def register(payload: RegisterInput, request: Request, db: Db):
    if not request.app.state.settings.registration_enabled:
        raise ApiError(404, "NOT_FOUND", "Registration is unavailable")
    auth_limit(request, db, "register", payload.email)
    accounts.register(db, request.app.state.settings, payload)
    return MessageView(
        message="If registration is available for this email, "
        "verification instructions have been queued"
    )


@router.post("/login", response_model=SessionView)
def login(payload: LoginInput, request: Request, response: Response, db: Db):
    auth_limit(request, db, "login", payload.email)
    settings = request.app.state.settings
    session, merchant, token, csrf = accounts.login(db, settings, payload)
    age = max(0, int((session.expires_at - datetime.now(UTC)).total_seconds()))
    for name, value, hidden in [(SESSION_COOKIE, token, True), (CSRF_COOKIE, csrf, False)]:
        response.set_cookie(
            name,
            value,
            max_age=age,
            httponly=hidden,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/",
        )
    return SessionView(
        merchant_id=merchant.id,
        merchant_name=merchant.name,
        timezone=merchant.timezone,
        expires_at=session.expires_at,
        is_demo=False,
    )


@router.post("/verify", response_model=MessageView)
def verify(payload: TokenInput, request: Request, db: Db):
    auth_limit(request, db, "verify", digest(payload.token))
    accounts.consume_account_token(db, payload.token, "VERIFY")
    return MessageView(message="Email verified. You can now sign in.")


@router.post("/forgot-password", response_model=MessageView, status_code=202)
def forgot(payload: EmailInput, request: Request, db: Db):
    auth_limit(request, db, "recovery", payload.email)
    accounts.request_recovery(db, request.app.state.settings, payload.email)
    return MessageView(message="If the account exists, recovery instructions have been queued")


@router.post("/resend-verification", response_model=MessageView, status_code=202)
def resend(payload: EmailInput, request: Request, db: Db):
    auth_limit(request, db, "resend", payload.email)
    accounts.request_recovery(db, request.app.state.settings, payload.email, "VERIFY")
    return MessageView(message="If the account exists, verification instructions have been queued")


@router.post("/reset-password", response_model=MessageView)
def reset(payload: PasswordResetInput, request: Request, db: Db):
    auth_limit(request, db, "reset", digest(payload.token))
    accounts.consume_account_token(db, payload.token, "RESET", payload.password)
    return MessageView(message="Password updated. All previous sessions were revoked.")


@router.post("/logout-all", response_model=MessageView)
def logout_all(actor: CurrentActor, db: Db):
    lock_merchant(db, actor)
    current = db.get(DemoSession, actor.session_id)
    predicate = (
        DemoSession.user_id == current.user_id if current.user_id else DemoSession.id == current.id
    )
    db.execute(
        update(DemoSession)
        .where(DemoSession.merchant_id == actor.merchant_id, predicate)
        .values(revoked=True)
    )
    audit(db, actor, "ALL_SESSIONS_REVOKED", actor.merchant_id)
    db.commit()
    return MessageView(message="Sessions revoked")


@router.get("/dev-inbox", response_model=list[DevEmailView])
def dev_inbox(request: Request, db: Db, email: Annotated[str, Query(min_length=3, max_length=254)]):
    settings = request.app.state.settings
    if not local_inbox_enabled(settings):
        raise ApiError(404, "NOT_FOUND", "Endpoint not available")
    origin_guard(request)
    rows = db.scalars(
        select(EmailOutbox)
        .where(EmailOutbox.recipient == email.casefold())
        .order_by(EmailOutbox.created_at.desc())
        .limit(20)
    ).all()
    decryptor = cipher(settings)
    return [
        DevEmailView(
            id=row.id,
            recipient=row.recipient,
            subject=row.subject,
            body=decryptor.decrypt(row.encrypted_body.encode()).decode(),
            status=row.status,
        )
        for row in rows
    ]
