import runpy
import secrets
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr, ValidationError
from sqlalchemy import create_engine, text

from app.core.config import Settings


def test_readiness_and_metrics_access(business):
    client, _, app = business
    assert client.get("/api/v1/health/ready").status_code == 200
    app.state.settings.metrics_token = SecretStr("local-metrics-token")
    assert client.get("/api/v1/metrics").status_code == 401
    response = client.get(
        "/api/v1/metrics", headers={"Authorization": "Bearer local-metrics-token"}
    )
    assert response.status_code == 200 and "bizbazaar_mail_pending 0" in response.text


def test_production_configuration_requires_private_settings():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production")
    settings = Settings(
        _env_file=None,
        app_env="production",
        cookie_secure=True,
        demo_enabled=False,
        public_base_url="https://shop.example.com",
        allowed_origins=["https://shop.example.com"],
        database_url="postgresql+psycopg://bizbazaar_runtime:private-test-password@db/bizbazaar",
        mail_encryption_key=Fernet.generate_key().decode(),
        mail_delivery_mode="smtp",
        smtp_host="smtp.example.com",
        metrics_token=secrets.token_urlsafe(32),
    )
    assert settings.app_env == "production"


def test_runtime_role_cannot_change_audit_or_financial_history(database, monkeypatch):
    password = secrets.token_urlsafe(32)
    monkeypatch.setenv("RUNTIME_DB_PASSWORD", password)
    runpy.run_path(
        str(Path(__file__).resolve().parents[3] / "scripts/provision_runtime_role.py"),
        run_name="__main__",
    )
    url = database.url.set(username="bizbazaar_runtime", password=password)
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            permissions = connection.execute(
                text("""SELECT
              has_table_privilege(current_user, 'credit_events', 'UPDATE'),
              has_table_privilege(current_user, 'audit_logs', 'DELETE'),
              has_table_privilege(current_user, 'products', 'INSERT')""")
            ).one()
            assert permissions == (False, False, True)
            role = connection.execute(
                text(
                    "SELECT rolsuper, rolcreatedb, rolcreaterole "
                    "FROM pg_roles WHERE rolname=current_user"
                )
            ).one()
            assert role == (False, False, False)
    finally:
        engine.dispose()
