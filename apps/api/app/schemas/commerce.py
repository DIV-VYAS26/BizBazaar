from datetime import date as CalendarDate
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, EmailStr, Field, field_validator, model_validator

from .api import Identifier, Money, StrictModel

NonnegativeMoney = Annotated[int, Field(strict=True, ge=0, le=1_000_000_000_000)]
Quantity = Annotated[int, Field(strict=True, ge=1, le=10000)]


class CustomerCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None
    request_marketing_consent: bool = Field(strict=True, default=False)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.casefold() if value else None

    @model_validator(mode="after")
    def consent_needs_email(self):
        if self.request_marketing_consent and not self.email:
            raise ValueError("Email is required to request marketing consent")
        return self


class CustomerView(StrictModel):
    id: UUID
    name: str
    email: str | None
    marketing_opt_in: bool
    consent_at: datetime | None


class ProductCreate(StrictModel):
    sku: Identifier
    name: str = Field(min_length=1, max_length=120)
    selling_price_paise: Money
    unit_cost_paise: NonnegativeMoney | None = None
    stock_quantity: Annotated[int, Field(strict=True, ge=0, le=1_000_000)] | None = None
    active: bool = Field(strict=True, default=True)


class ProductUpdate(ProductCreate):
    version: Annotated[int, Field(strict=True, ge=1)]


class ProductView(ProductCreate):
    id: UUID
    version: int


class BasketLine(StrictModel):
    product_id: UUID
    quantity: Quantity


class Basket(StrictModel):
    lines: list[BasketLine] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_products(self):
        ids = [row.product_id for row in self.lines]
        if len(ids) != len(set(ids)):
            raise ValueError("A product may occur only once in a basket")
        return self


class OfferRule(StrictModel):
    type: Literal["FIXED", "PERCENT", "BOGO", "BUNDLE", "THRESHOLD"]
    discount_paise: NonnegativeMoney = 0
    percentage_bps: Annotated[int, Field(strict=True, ge=0, le=10000)] = 0
    bundle_price_paise: NonnegativeMoney | None = None
    threshold_paise: NonnegativeMoney | None = None

    @model_validator(mode="after")
    def consistent_parameters(self):
        if self.type == "BUNDLE" and self.bundle_price_paise is None:
            raise ValueError("Bundle price is required")
        if self.type == "THRESHOLD" and not self.threshold_paise:
            raise ValueError("Positive purchase threshold is required")
        return self


class OfferEvaluate(Basket):
    rule: OfferRule
    minimum_margin_bps: Annotated[int, Field(strict=True, ge=0, le=10000)] = 2000


class OfferQuote(StrictModel):
    subtotal_paise: int
    discount_paise: int
    revenue_paise: int
    cost_paise: int | None
    profit_paise: int | None
    margin_bps: int | None
    eligible: bool
    violations: list[str]
    product_versions: dict[str, int]


class OfferCreate(OfferEvaluate):
    name: str = Field(min_length=1, max_length=120)
    budget_cap_paise: NonnegativeMoney
    max_redemptions: Quantity
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def valid_period(self):
        if (
            self.ends_at <= self.starts_at
            or (self.ends_at - self.starts_at).total_seconds() > 90 * 86400
        ):
            raise ValueError("Offer duration must be positive and at most 90 days")
        return self


class OfferView(StrictModel):
    id: UUID
    name: str
    status: str
    quote: OfferQuote
    specification: dict
    budget_cap_paise: int
    max_redemptions: int
    redemption_count: int
    discount_spent_paise: int
    starts_at: datetime
    ends_at: datetime


class SaleCreate(Basket):
    request_key: Identifier
    customer_id: UUID | None = None
    payment_method: Literal["CASH", "OTHER", "CREDIT"] = "CASH"
    due_date: CalendarDate | None = None
    offer_id: UUID | None = None
    redeem_points: Annotated[int, Field(strict=True, ge=0, le=1_000_000)] = 0

    @model_validator(mode="after")
    def valid_credit(self):
        if self.payment_method == "CREDIT" and (not self.customer_id or not self.due_date):
            raise ValueError("Credit sales require a customer and due date")
        if self.payment_method == "CREDIT" and self.redeem_points:
            raise ValueError("Points can be redeemed only on immediately paid sales")
        return self


class SaleView(StrictModel):
    id: UUID
    customer_id: UUID | None
    payment_method: str
    status: str
    subtotal_paise: int
    discount_paise: int
    total_paise: int
    cost_paise: int | None
    profit_paise: int | None
    redeemed_points: int
    created_at: datetime


class CreditPost(StrictModel):
    request_key: Identifier
    amount_paise: Money
    due_date: CalendarDate | None = None
    note: str = Field(default="", max_length=300)


class ReversalInput(StrictModel):
    request_key: Identifier
    note: str = Field(min_length=1, max_length=300)


class CreditEventView(StrictModel):
    id: UUID
    kind: str
    delta_paise: int
    due_date: CalendarDate | None
    note: str
    reverses_id: UUID | None
    created_at: datetime
    acknowledgement: str = "PENDING"


class CreditLedgerView(StrictModel):
    customer: CustomerView
    balance_paise: int
    overdue_paise: int
    events: list[CreditEventView]


class PortalDecision(StrictModel):
    event_id: UUID
    decision: Literal["ACKNOWLEDGED", "DISPUTED"]
    note: str = Field(default="", max_length=300)


class LoyaltySettings(StrictModel):
    enabled: bool = Field(strict=True, default=False)
    earning_spend_paise: Money = 10000
    earning_points: Quantity = 1
    point_value_paise: Money = 100
    minimum_margin_bps: Annotated[int, Field(strict=True, ge=0, le=10000)] = 2000


class LoyaltyEventView(StrictModel):
    id: UUID
    sale_id: UUID
    points_delta: int
    kind: str
    created_at: datetime


class LoyaltyBalance(StrictModel):
    balance_points: int
    available_points: int
    events: list[LoyaltyEventView]


class RetentionCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=160, pattern=r"^[^\r\n]+$")
    body: str = Field(min_length=1, max_length=1000)
    inactive_days: Annotated[int, Field(strict=True, ge=7, le=365)] = 30
    customer_ids: list[UUID] = Field(min_length=1, max_length=100)


class RetentionView(StrictModel):
    id: UUID
    name: str
    subject: str
    body: str
    inactive_days: int
    customer_ids: list[str]
    status: str
    queued_count: int


class OutboxView(StrictModel):
    id: UUID
    recipient: str
    subject: str
    kind: str
    status: str
    attempts: int
    created_at: datetime
