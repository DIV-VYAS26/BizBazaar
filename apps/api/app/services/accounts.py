import secrets
from datetime import UTC, datetime, timedelta
from threading import BoundedSemaphore

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.core.errors import ApiError
from app.core.security import Actor, digest
from app.db.commerce import AccountToken, AccountUser, RateBucket
from app.db.models import DemoSession, Merchant
from app.services.mail import cipher, queue_email
from app.services.transactions import audit

PASSWORD_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
DUMMY_HASH = PASSWORD_HASHER.hash(secrets.token_urlsafe(32))
HASH_SLOTS = BoundedSemaphore(4)


def password_operation(method, *arguments):
    # Bound Argon2 memory use across FastAPI worker threads.
    if not HASH_SLOTS.acquire(blocking=False):
        raise ApiError(503, "AUTH_BUSY", "Authentication is busy; retry shortly")
    try:
        return method(*arguments)
    finally:
        HASH_SLOTS.release()


def enforce_auth_limit(db, operation, email, client_ip):
    now = datetime.now(UTC)
    bucket = int(now.timestamp()) // 900
    for subject, limit in [(email, 10), (client_ip, 60)]:
        key = digest(f"{operation}:{subject}:{bucket}")
        statement = insert(RateBucket).values(
            key=key, count=1, expires_at=now + timedelta(minutes=30)
        )
        count = db.scalar(
            statement.on_conflict_do_update(
                index_elements=[RateBucket.key], set_={"count": RateBucket.count + 1}
            ).returning(RateBucket.count)
        )
        db.commit()  # Failed attempts must remain counted even if authentication fails.
        if count > limit:
            raise ApiError(429, "AUTH_RATE_LIMITED", "Too many attempts; try again later")


def issue_account_token(db, settings, user, purpose):
    now = datetime.now(UTC)
    db.execute(
        update(AccountToken)
        .where(
            AccountToken.user_id == user.id,
            AccountToken.purpose == purpose,
            AccountToken.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    raw = secrets.token_urlsafe(32)
    row = AccountToken(
        user_id=user.id,
        purpose=purpose,
        token_hash=digest(raw),
        expires_at=now + timedelta(minutes=30),
    )
    db.add(row)
    db.flush()
    flow = "verify" if purpose == "VERIFY" else "reset"
    link = f"{settings.public_base_url.rstrip('/')}/account#flow={flow}&token={raw}"
    queue_email(
        db,
        settings,
        user.merchant_id,
        user.email,
        "Verify your BizBazaar email" if purpose == "VERIFY" else "Reset your BizBazaar password",
        f"Open this single-use link within 30 minutes:\n{link}\n"
        "Ignore this message if you did not request it.",
        purpose,
        f"account:{row.id}",
    )


def register(db, settings, payload):
    cipher(settings)  # Fail before creating an account if its verification cannot be delivered.
    password_hash = password_operation(PASSWORD_HASHER.hash, payload.password.get_secret_value())
    # Advisory lock serializes concurrent registration without exposing unique-constraint failures.
    from sqlalchemy import text

    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:email, 0))"), {"email": payload.email}
    )
    existing = db.scalar(select(AccountUser).where(AccountUser.email == payload.email))
    if existing is not None:
        db.rollback()
        return
    merchant = Merchant(name=payload.merchant_name)
    db.add(merchant)
    db.flush()
    user = AccountUser(merchant_id=merchant.id, email=payload.email, password_hash=password_hash)
    db.add(user)
    db.flush()
    issue_account_token(db, settings, user, "VERIFY")
    db.commit()


def login(db, settings, payload):
    user = db.scalar(select(AccountUser).where(AccountUser.email == payload.email))
    valid = False
    try:
        valid = password_operation(
            PASSWORD_HASHER.verify,
            user.password_hash if user else DUMMY_HASH,
            payload.password.get_secret_value(),
        )
    except (VerificationError, InvalidHashError):
        pass
    if not valid or user is None or user.disabled or user.verified_at is None:
        db.rollback()
        raise ApiError(
            401, "INVALID_LOGIN", "Email or password is invalid, or verification is required"
        )
    # Lock order matches every other mutation: merchant first, then account/session.
    merchant = db.scalar(select(Merchant).where(Merchant.id == user.merchant_id).with_for_update())
    user = db.scalar(
        select(AccountUser)
        .where(AccountUser.id == user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    # Reset may have changed the password while this login was waiting.
    try:
        valid = password_operation(
            PASSWORD_HASHER.verify, user.password_hash, payload.password.get_secret_value()
        )
    except (VerificationError, InvalidHashError):
        valid = False
    if not valid or user.disabled or user.verified_at is None:
        raise ApiError(
            401, "INVALID_LOGIN", "Email or password is invalid, or verification is required"
        )
    if PASSWORD_HASHER.check_needs_rehash(user.password_hash):
        user.password_hash = password_operation(
            PASSWORD_HASHER.hash, payload.password.get_secret_value()
        )
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    session = DemoSession(
        merchant_id=user.merchant_id,
        user_id=user.id,
        kind="MERCHANT",
        token_hash=digest(token),
        csrf_hash=digest(csrf),
        expires_at=datetime.now(UTC) + timedelta(hours=settings.session_hours),
    )
    db.add(session)
    db.flush()
    audit(db, Actor(user.merchant_id, session.id), "ACCOUNT_LOGIN", user.id)
    db.commit()
    return session, merchant, token, csrf


def request_recovery(db, settings, email, purpose="RESET"):
    cipher(settings)
    user = db.scalar(select(AccountUser).where(AccountUser.email == email))
    if user is not None and not user.disabled:
        # Per-account serialization also makes token invalidation deterministic.
        db.scalar(select(Merchant).where(Merchant.id == user.merchant_id).with_for_update())
        issue_account_token(db, settings, user, purpose)
    db.commit()


def consume_account_token(db, raw, purpose, new_password=None):
    preview = db.scalar(
        select(AccountToken).where(
            AccountToken.token_hash == digest(raw), AccountToken.purpose == purpose
        )
    )
    if preview is None:
        raise ApiError(422, "INVALID_TOKEN", "Link is invalid or expired")
    user = db.get(AccountUser, preview.user_id)
    db.scalar(select(Merchant).where(Merchant.id == user.merchant_id).with_for_update())
    token = db.scalar(
        select(AccountToken)
        .where(AccountToken.id == preview.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    now = datetime.now(UTC)
    if token.consumed_at is not None or token.expires_at <= now or user.disabled:
        raise ApiError(422, "INVALID_TOKEN", "Link is invalid or expired")
    token.consumed_at = now
    if purpose == "VERIFY":
        user.verified_at = now
    else:
        user.password_hash = password_operation(
            PASSWORD_HASHER.hash, new_password.get_secret_value()
        )
        db.execute(update(DemoSession).where(DemoSession.user_id == user.id).values(revoked=True))
        db.execute(
            update(AccountToken)
            .where(
                AccountToken.user_id == user.id,
                AccountToken.purpose == "RESET",
                AccountToken.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
    db.commit()
