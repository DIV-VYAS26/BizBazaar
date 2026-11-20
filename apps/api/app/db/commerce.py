from datetime import date, datetime
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
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base, utcnow


class AccountUser(Base):
    __tablename__ = "account_users"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AccountToken(Base):
    __tablename__ = "account_tokens"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("account_users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(12))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("merchant_id", "id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254))
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_marketing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CustomerToken(Base):
    __tablename__ = "customer_tokens"
    __table_args__ = (
        ForeignKeyConstraint(
            ["merchant_id", "customer_id"], ["customers.merchant_id", "customers.id"]
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"))
    customer_id: Mapped[UUID] = mapped_column()
    purpose: Mapped[str] = mapped_column(String(16))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailOutbox(Base):
    __tablename__ = "email_outbox"
    __table_args__ = (
        Index("ix_outbox_delivery", "status", "next_attempt_at"),
        ForeignKeyConstraint(
            ["merchant_id", "customer_id"], ["customers.merchant_id", "customers.id"]
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    customer_id: Mapped[UUID | None] = mapped_column()
    recipient: Mapped[str] = mapped_column(String(254), index=True)
    subject: Mapped[str] = mapped_column(String(160))
    encrypted_body: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20))
    dedup_key: Mapped[str] = mapped_column(String(160), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="QUEUED")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("merchant_id", "id"),
        UniqueConstraint("merchant_id", "sku"),
        CheckConstraint("selling_price_paise > 0 AND selling_price_paise <= 1000000000000"),
        CheckConstraint("unit_cost_paise IS NULL OR unit_cost_paise >= 0"),
        CheckConstraint("stock_quantity IS NULL OR stock_quantity >= 0"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    sku: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(120))
    selling_price_paise: Mapped[int] = mapped_column(BigInteger)
    unit_cost_paise: Mapped[int | None] = mapped_column(BigInteger)
    stock_quantity: Mapped[int | None] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class BusinessRequest(Base):
    __tablename__ = "business_requests"
    __table_args__ = (UniqueConstraint("merchant_id", "request_key"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"))
    request_key: Mapped[str] = mapped_column(String(100))
    scope: Mapped[str] = mapped_column(String(100))
    fingerprint: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSONB)


class CreditAccount(Base):
    __tablename__ = "credit_accounts"
    __table_args__ = (
        UniqueConstraint("merchant_id", "id"),
        UniqueConstraint("merchant_id", "customer_id"),
        ForeignKeyConstraint(
            ["merchant_id", "customer_id"], ["customers.merchant_id", "customers.id"]
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    customer_id: Mapped[UUID] = mapped_column()


class CreditEvent(Base):
    __tablename__ = "credit_events"
    __table_args__ = (
        UniqueConstraint("merchant_id", "id"),
        UniqueConstraint("reverses_id"),
        ForeignKeyConstraint(
            ["merchant_id", "account_id"], ["credit_accounts.merchant_id", "credit_accounts.id"]
        ),
        ForeignKeyConstraint(
            ["merchant_id", "reverses_id"], ["credit_events.merchant_id", "credit_events.id"]
        ),
        CheckConstraint("kind IN ('CHARGE','REPAYMENT','REVERSAL')"),
        CheckConstraint("delta_paise <> 0"),
        CheckConstraint(
            "(kind <> 'CHARGE' OR delta_paise > 0) AND (kind <> 'REPAYMENT' OR delta_paise < 0)"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"))
    account_id: Mapped[UUID] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(16))
    delta_paise: Mapped[int] = mapped_column(BigInteger)
    due_date: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str] = mapped_column(String(300), default="")
    reverses_id: Mapped[UUID | None] = mapped_column()
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("demo_sessions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CreditAcknowledgement(Base):
    __tablename__ = "credit_acknowledgements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["merchant_id", "event_id"], ["credit_events.merchant_id", "credit_events.id"]
        ),
        ForeignKeyConstraint(
            ["merchant_id", "customer_id"], ["customers.merchant_id", "customers.id"]
        ),
        UniqueConstraint("event_id"),
        CheckConstraint("decision IN ('ACKNOWLEDGED','DISPUTED')"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"))
    event_id: Mapped[UUID] = mapped_column()
    customer_id: Mapped[UUID] = mapped_column()
    decision: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProfitOffer(Base):
    __tablename__ = "profit_offers"
    __table_args__ = (
        UniqueConstraint("merchant_id", "id"),
        CheckConstraint("status IN ('DRAFT','APPROVED','ACTIVE','COMPLETED')"),
        CheckConstraint("discount_spent_paise >= 0 AND discount_spent_paise <= budget_cap_paise"),
        CheckConstraint("redemption_count >= 0 AND redemption_count <= max_redemptions"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(12), default="DRAFT")
    specification: Mapped[dict] = mapped_column(JSONB)
    quote: Mapped[dict] = mapped_column(JSONB)
    product_versions: Mapped[dict] = mapped_column(JSONB)
    budget_cap_paise: Mapped[int] = mapped_column(BigInteger)
    max_redemptions: Mapped[int] = mapped_column(Integer)
    discount_spent_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    redemption_count: Mapped[int] = mapped_column(Integer, default=0)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        UniqueConstraint("merchant_id", "id"),
        ForeignKeyConstraint(
            ["merchant_id", "customer_id"], ["customers.merchant_id", "customers.id"]
        ),
        ForeignKeyConstraint(
            ["merchant_id", "offer_id"], ["profit_offers.merchant_id", "profit_offers.id"]
        ),
        CheckConstraint("total_paise > 0 AND discount_paise >= 0"),
        CheckConstraint("subtotal_paise - discount_paise = total_paise"),
        CheckConstraint("payment_method IN ('CASH','OTHER','CREDIT')"),
        CheckConstraint("status IN ('RECORDED','VOIDED')"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    customer_id: Mapped[UUID | None] = mapped_column()
    offer_id: Mapped[UUID | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(12), default="RECORDED")
    payment_method: Mapped[str] = mapped_column(String(12))
    subtotal_paise: Mapped[int] = mapped_column(BigInteger)
    discount_paise: Mapped[int] = mapped_column(BigInteger)
    total_paise: Mapped[int] = mapped_column(BigInteger)
    cost_paise: Mapped[int | None] = mapped_column(BigInteger)
    redeemed_points: Mapped[int] = mapped_column(Integer, default=0)
    credit_event_id: Mapped[UUID | None] = mapped_column(ForeignKey("credit_events.id"))
    transaction_pk: Mapped[UUID | None] = mapped_column(ForeignKey("transactions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    @property
    def profit_paise(self):
        return (
            self.total_paise - self.cost_paise
            if self.cost_paise is not None and self.status != "VOIDED"
            else None
        )


class SaleLine(Base):
    __tablename__ = "sale_lines"
    __table_args__ = (
        ForeignKeyConstraint(["merchant_id", "sale_id"], ["sales.merchant_id", "sales.id"]),
        ForeignKeyConstraint(
            ["merchant_id", "product_id"], ["products.merchant_id", "products.id"]
        ),
        CheckConstraint("quantity > 0 AND unit_price_paise > 0"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"))
    sale_id: Mapped[UUID] = mapped_column()
    product_id: Mapped[UUID] = mapped_column()
    product_name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_paise: Mapped[int] = mapped_column(BigInteger)
    unit_cost_paise: Mapped[int | None] = mapped_column(BigInteger)


class LoyaltyPolicy(Base):
    __tablename__ = "loyalty_policies"
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    earning_spend_paise: Mapped[int] = mapped_column(BigInteger)
    earning_points: Mapped[int] = mapped_column(Integer)
    point_value_paise: Mapped[int] = mapped_column(BigInteger)
    minimum_margin_bps: Mapped[int] = mapped_column(Integer)


class LoyaltyEvent(Base):
    __tablename__ = "loyalty_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["merchant_id", "customer_id"], ["customers.merchant_id", "customers.id"]
        ),
        ForeignKeyConstraint(["merchant_id", "sale_id"], ["sales.merchant_id", "sales.id"]),
        UniqueConstraint("merchant_id", "source_key"),
        CheckConstraint("points_delta <> 0"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    customer_id: Mapped[UUID] = mapped_column()
    sale_id: Mapped[UUID] = mapped_column()
    points_delta: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(16))
    source_key: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RetentionCampaign(Base):
    __tablename__ = "retention_campaigns"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    subject: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(1000))
    inactive_days: Mapped[int] = mapped_column(Integer)
    customer_ids: Mapped[list] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(12), default="DRAFT")
    queued_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
