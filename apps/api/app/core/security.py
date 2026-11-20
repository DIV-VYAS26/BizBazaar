import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.commerce import AccountUser
from app.db.models import DemoSession, Merchant
from app.db.session import get_db

SESSION_COOKIE = "bizbazaar_session"
CSRF_COOKIE = "bizbazaar_csrf"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class Actor:
    merchant_id: UUID
    session_id: UUID


def authenticate(request: Request, db: Session = Depends(get_db)) -> Actor:
    token = request.cookies.get(SESSION_COOKIE, "")
    if not 40 <= len(token) <= 100:
        raise ApiError(401, "UNAUTHENTICATED", "A valid merchant session is required")
    row = db.scalar(select(DemoSession).where(DemoSession.token_hash == digest(token)))
    if row is None or row.revoked or row.expires_at <= datetime.now(UTC):
        raise ApiError(401, "UNAUTHENTICATED", "Session is invalid or expired")
    if row.kind == "DEMO" and not request.app.state.settings.demo_enabled:
        raise ApiError(401, "UNAUTHENTICATED", "Demo sessions are disabled")
    validate_account_session(db, row)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(digest(csrf), row.csrf_hash):
            raise ApiError(403, "CSRF_FAILED", "Valid CSRF proof is required")
        origin = request.headers.get("origin")
        if origin not in request.app.state.settings.allowed_origins:
            raise ApiError(403, "ORIGIN_REJECTED", "Browser origin is not permitted")
    return Actor(row.merchant_id, row.id)


def validate_account_session(db, row):
    if row.kind == "MERCHANT":
        user = db.get(AccountUser, row.user_id, populate_existing=True)
        if (
            user is None
            or user.disabled
            or user.verified_at is None
            or user.merchant_id != row.merchant_id
        ):
            raise ApiError(401, "UNAUTHENTICATED", "Merchant account is unavailable")


def lock_merchant(db: Session, actor: Actor) -> Merchant:
    merchant = db.scalar(select(Merchant).where(Merchant.id == actor.merchant_id).with_for_update())
    if merchant is None:
        raise ApiError(401, "UNAUTHENTICATED", "Merchant session is no longer valid")
    # Mutations serialize per merchant: a simple, explicit MVP concurrency policy.
    # Recheck revocation after waiting so a completed logout takes effect.
    row = db.scalar(
        select(DemoSession)
        .where(DemoSession.id == actor.session_id)
        .execution_options(populate_existing=True)
    )
    if row is None or row.revoked or row.expires_at <= datetime.now(UTC):
        raise ApiError(401, "UNAUTHENTICATED", "Session is invalid or expired")
    validate_account_session(db, row)
    return merchant
