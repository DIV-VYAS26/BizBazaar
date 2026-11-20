import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings, get_settings
from app.core.security import CSRF_COOKIE, SESSION_COOKIE, Actor, digest
from app.db.models import Base, DemoSession, Merchant
from app.db.session import get_db
from app.main import create_app


@pytest.fixture(scope="session")
def pg_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL database ending in _test")
    parsed = make_url(url)
    if not parsed.database or not parsed.database.endswith("_test"):
        pytest.fail("Refusing destructive tests: database name must end in _test")
    original = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()
    if original is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = original
    get_settings.cache_clear()


@pytest.fixture
def database(pg_engine):
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with pg_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} CASCADE"))
    return pg_engine


def add_actor(engine, name="Shop"):
    token = "test-" + uuid4().hex + uuid4().hex
    csrf = "csrf-" + uuid4().hex
    with Session(engine) as db:
        merchant = Merchant(name=name)
        db.add(merchant)
        db.flush()
        session = DemoSession(
            merchant_id=merchant.id,
            token_hash=digest(token),
            csrf_hash=digest(csrf),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db.add(session)
        db.flush()
        actor = Actor(merchant.id, session.id)
        db.commit()
    return actor, token, csrf


@pytest.fixture
def actor(database):
    return add_actor(database)[0]


@pytest.fixture
def client_bundle(database):
    actor, token, csrf = add_actor(database)
    app = create_app(Settings(app_env="test", demo_enabled=True, analytics_mode="unavailable"))

    def override_db():
        with Session(database, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=False) as client:
        client.cookies.set(SESSION_COOKIE, token)
        client.cookies.set(CSRF_COOKIE, csrf)
        client.headers.update({"Origin": "http://localhost:3000", "X-CSRF-Token": csrf})
        yield client, actor, app


@pytest.fixture
def business(client_bundle):
    from cryptography.fernet import Fernet
    from pydantic import SecretStr

    client, actor, app = client_bundle
    app.state.settings.mail_encryption_key = SecretStr(Fernet.generate_key().decode())
    return client, actor, app
