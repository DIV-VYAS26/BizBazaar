from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Merchant(Base):
    __tablename__ = "merchants"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")


class DemoSession(Base):
    __tablename__ = "demo_sessions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("account_users.id"))
    kind: Mapped[str] = mapped_column(String(12), default="DEMO", server_default="DEMO")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("merchant_id", "transaction_id"),
        UniqueConstraint("merchant_id", "id"),
        CheckConstraint("amount_paise > 0 AND amount_paise <= 1000000000000"),
        CheckConstraint("currency = 'INR'"),
        CheckConstraint("status IN ('SUCCESS','PENDING','FAILED','REFUNDED')"),
        CheckConstraint("source IN ('CSV','SIMULATOR','MANUAL')", name="ck_transaction_source"),
        CheckConstraint("is_simulated = (source = 'SIMULATOR')"),
        Index("ix_transactions_merchant_timestamp", "merchant_id", "timestamp"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"))
    transaction_id: Mapped[str] = mapped_column(String(100))
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(12))
    source: Mapped[str] = mapped_column(String(12))
    is_simulated: Mapped[bool] = mapped_column(Boolean)


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        UniqueConstraint("merchant_id", "id"),
        CheckConstraint("type IN ('NTH_PAYMENT','COLLECTION_THRESHOLD')"),
        CheckConstraint("status IN ('DRAFT','APPROVED','ACTIVE','COMPLETED')"),
        CheckConstraint("ends_at > starts_at"),
        CheckConstraint("reward_cost_paise > 0 AND budget_cap_paise >= reward_cost_paise"),
        CheckConstraint("budget_cap_paise <= 1000000000000"),
        CheckConstraint("consumed_paise >= 0 AND reserved_paise >= 0"),
        CheckConstraint("consumed_paise + reserved_paise <= budget_cap_paise"),
        CheckConstraint("eligible_count >= 0 AND cumulative_paise >= 0"),
        Index(
            "uq_one_active_campaign",
            "merchant_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(12), default="DRAFT")
    rule_parameters: Mapped[dict] = mapped_column(JSONB)
    reward_cost_paise: Mapped[int] = mapped_column(BigInteger)
    budget_cap_paise: Mapped[int] = mapped_column(BigInteger)
    consumed_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    reserved_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("demo_sessions.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    eligible_count: Mapped[int] = mapped_column(BigInteger, default=0)
    cumulative_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    threshold_awarded: Mapped[bool] = mapped_column(Boolean, default=False)


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("merchant_id", "event_id"),
        ForeignKeyConstraint(
            ["merchant_id", "transaction_pk"], ["transactions.merchant_id", "transactions.id"]
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"))
    event_id: Mapped[str] = mapped_column(String(100))
    transaction_pk: Mapped[UUID] = mapped_column()
    fingerprint: Mapped[str] = mapped_column(String(64))
    decision: Mapped[dict] = mapped_column(JSONB)


class ProcessedTransaction(Base):
    __tablename__ = "processed_transactions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["merchant_id", "transaction_pk"], ["transactions.merchant_id", "transactions.id"]
        ),
        ForeignKeyConstraint(
            ["merchant_id", "campaign_id"], ["campaigns.merchant_id", "campaigns.id"]
        ),
        UniqueConstraint("merchant_id", "transaction_pk"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"))
    transaction_pk: Mapped[UUID] = mapped_column()
    campaign_id: Mapped[UUID | None] = mapped_column()
    acceptance_sequence: Mapped[int | None] = mapped_column(BigInteger)


class Reward(Base):
    __tablename__ = "rewards"
    __table_args__ = (
        ForeignKeyConstraint(
            ["merchant_id", "campaign_id"], ["campaigns.merchant_id", "campaigns.id"]
        ),
        ForeignKeyConstraint(
            ["merchant_id", "transaction_pk"], ["transactions.merchant_id", "transactions.id"]
        ),
        UniqueConstraint("campaign_id", "transaction_pk"),
        CheckConstraint("cost_paise > 0"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    campaign_id: Mapped[UUID] = mapped_column()
    transaction_pk: Mapped[UUID] = mapped_column()
    cost_paise: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(24), default="SIMULATED_ISSUED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("demo_sessions.id"))
    actor_type: Mapped[str] = mapped_column(String(16), default="SESSION", server_default="SESSION")
    action: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(100))
    changes: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Coverage(Base):
    __tablename__ = "coverage"
    __table_args__ = (
        UniqueConstraint("merchant_id", "date", "includes_simulated"),
        CheckConstraint("status IN ('COMPLETE','PARTIAL','UNKNOWN')"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"))
    date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12))
    provenance: Mapped[str] = mapped_column(String(200))
    includes_simulated: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )


class MerchantSettings(Base):
    __tablename__ = "merchant_settings"
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), primary_key=True)
    promotion: Mapped[dict] = mapped_column(JSONB)
