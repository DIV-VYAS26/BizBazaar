from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, TypeVar
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    model_validator,
)

Money = Annotated[int, Field(strict=True, gt=0, le=1_000_000_000_000)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,100}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class PaymentStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PENDING = "PENDING"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class CampaignType(StrEnum):
    NTH_PAYMENT = "NTH_PAYMENT"
    COLLECTION_THRESHOLD = "COLLECTION_THRESHOLD"


class CampaignStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class NthRule(StrictModel):
    n: Annotated[int, Field(strict=True, ge=1, le=1_000_000)]


class ThresholdRule(StrictModel):
    threshold_paise: Money


class CampaignCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    type: CampaignType
    rule_parameters: NthRule | ThresholdRule
    reward_cost_paise: Money
    budget_cap_paise: Money
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def validate_rules(self):
        expected = NthRule if self.type == CampaignType.NTH_PAYMENT else ThresholdRule
        if not isinstance(self.rule_parameters, expected):
            raise ValueError("Rule parameters must match the campaign type")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if (self.ends_at - self.starts_at).days > 90:
            raise ValueError("Campaign duration cannot exceed 90 days")
        if self.budget_cap_paise < self.reward_cost_paise:
            raise ValueError("Budget must cover at least one reward")
        return self


class CampaignView(StrictModel):
    id: UUID
    name: str
    type: CampaignType
    status: CampaignStatus
    rule_parameters: dict[str, int]
    reward_cost_paise: int
    budget_cap_paise: int
    consumed_paise: int
    reserved_paise: int
    starts_at: datetime
    ends_at: datetime
    eligible_count: int
    cumulative_paise: int
    threshold_awarded: bool

    @computed_field
    @property
    def rewards_issued_count(self) -> int:
        return self.consumed_paise // self.reward_cost_paise


class SimulationPayment(StrictModel):
    event_id: Identifier
    transaction_id: Identifier
    amount_paise: Money
    timestamp: AwareDatetime
    status: PaymentStatus = PaymentStatus.SUCCESS


class PaymentDecision(StrictModel):
    event_id: str
    transaction_id: str
    campaign_id: UUID | None
    decision: Literal["ISSUED", "NOT_ELIGIBLE", "SKIPPED_BUDGET", "CAMPAIGN_INACTIVE"]
    reward_id: UUID | None
    acceptance_sequence: int | None
    is_simulated: Literal[True] = True
    reward_cost_paise: int = 0
    remaining_budget_paise: int | None = None
    eligible_count: int | None = None


class TransactionView(StrictModel):
    id: UUID
    transaction_id: str
    amount_paise: int
    currency: Literal["INR"]
    timestamp: datetime
    status: PaymentStatus
    source: Literal["CSV", "SIMULATOR", "MANUAL"]
    is_simulated: bool


class RewardView(StrictModel):
    id: UUID
    campaign_id: UUID
    transaction_pk: UUID
    transaction_id: str | None = None
    cost_paise: int
    status: Literal["SIMULATED_ISSUED"]
    created_at: datetime


T = TypeVar("T")


class Page[T](StrictModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class RowIssue(StrictModel):
    row: int
    kind: Literal["INVALID", "DUPLICATE", "CONFLICT"]
    field: str | None = None
    reason: str


class ImportReport(StrictModel):
    imported: int
    invalid: int
    duplicates: int
    conflicts: int
    issues: list[RowIssue]
    issues_truncated: bool
    coverage_status: Literal["UNKNOWN"] = "UNKNOWN"


class DemoLogin(StrictModel):
    token: str = Field(min_length=40, max_length=100)


class SessionView(StrictModel):
    merchant_id: UUID
    merchant_name: str
    timezone: str
    expires_at: datetime
    is_demo: bool = True


class HealthView(StrictModel):
    status: Literal["ok"] = "ok"
    service: Literal["bizbazaar-api"] = "bizbazaar-api"


class MessageView(StrictModel):
    message: str


class ReportView(StrictModel):
    campaign: CampaignView
    issued_count: int
    issued_cost_paise: int
    remaining_budget_paise: int
    observed_accepted_collections_paise: int
    is_simulated: Literal[True] = True
    limitations: list[str]


class AnalyticsEnvelope(StrictModel):
    status: Literal["AVAILABLE", "UNAVAILABLE"]
    generation_mode: Literal["REAL", "UNAVAILABLE"]
    start_date: date
    end_date: date
    timezone: str
    includes_simulated: bool
    result: dict[str, Any] | None
    limitations: list[str]


class ErrorBody(StrictModel):
    code: str
    message: str
    details: Any = None
    request_id: str


class ErrorEnvelope(StrictModel):
    error: ErrorBody
