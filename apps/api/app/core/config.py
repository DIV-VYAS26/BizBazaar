from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: Literal["local", "test", "production"] = "local"
    database_url: str = "postgresql+psycopg://bizbazaar:local-only@localhost:55432/bizbazaar"
    allowed_origins: list[str] = ["http://localhost:3000"]
    cookie_secure: bool = False
    demo_enabled: bool = False
    session_hours: int = Field(default=8, ge=1, le=24)
    analytics_mode: Literal["unavailable", "foundation", "real"] = "unavailable"
    max_body_bytes: int = Field(default=2_000_000, ge=1024, le=10_000_000)
    max_csv_rows: int = Field(default=5000, ge=1, le=10000)
    max_csv_field_chars: int = Field(default=512, ge=64, le=4096)
    max_report_days: int = Field(default=366, ge=1, le=366)
    public_base_url: str = "http://localhost:3000"
    registration_enabled: bool = True
    mail_encryption_key: SecretStr | None = None
    mail_delivery_mode: Literal["outbox", "smtp"] = "outbox"
    mail_from: str = "noreply@bizbazaar.example"
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    marketing_delivery_enabled: bool = False
    metrics_token: SecretStr | None = None

    @model_validator(mode="after")
    def deployment_boundary(self):
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("PostgreSQL with psycopg is required")
        if "*" in self.allowed_origins:
            raise ValueError("Explicit browser origins are required")
        from urllib.parse import urlsplit

        origin = urlsplit(self.public_base_url)
        if (
            origin.scheme not in {"http", "https"}
            or not origin.netloc
            or origin.username
            or origin.query
            or origin.fragment
            or origin.path not in {"", "/"}
        ):
            raise ValueError("PUBLIC_BASE_URL must be a fixed trusted HTTP(S) origin")
        if self.mail_encryption_key:
            from cryptography.fernet import Fernet

            Fernet(self.mail_encryption_key.get_secret_value().encode())
        if self.app_env == "production" and (
            not self.cookie_secure
            or self.demo_enabled
            or origin.scheme != "https"
            or any(not value.startswith("https://") for value in self.allowed_origins)
            or not self.mail_encryption_key
            or self.mail_delivery_mode != "smtp"
            or not self.smtp_host
            or not self.smtp_starttls
            or not self.metrics_token
            or "local-only" in self.database_url
        ):
            raise ValueError(
                "Production requires HTTPS, secure cookies, disabled demos, "
                "encrypted SMTP outbox, metrics secret and a private database"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
