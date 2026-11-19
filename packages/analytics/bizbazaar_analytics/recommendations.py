from datetime import timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from .context import prepare
from .metrics import calculate_metrics


class MerchantPromotion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    type: Literal["NTH_PAYMENT", "COLLECTION_THRESHOLD"]
    rule_parameters: dict[str, StrictInt]
    reward_cost_paise: int = Field(strict=True, gt=0, le=1_000_000_000_000)
    budget_cap_paise: int = Field(strict=True, gt=0, le=1_000_000_000_000)
    duration_days: int = Field(strict=True, ge=1, le=90)

    @model_validator(mode="after")
    def valid_rule(self):
        key = "n" if self.type == "NTH_PAYMENT" else "threshold_paise"
        limit = 1_000_000 if key == "n" else 1_000_000_000_000
        if (
            set(self.rule_parameters) != {key}
            or not 1 <= self.rule_parameters[key] <= limit
        ):
            raise ValueError("Invalid merchant-configured campaign rule")
        if self.reward_cost_paise > self.budget_cap_paise:
            raise ValueError("Budget cannot cover one reward")
        return self


def recommend_campaign(transactions, config, merchant_settings, context=None) -> dict:
    data = prepare(transactions, config, context)
    metrics = calculate_metrics(transactions, config, context)
    result = {
        "suggested_action": None,
        "explanation": "No campaign is suggested without recorded successful payments and explicit merchant settings.",
        "source_metrics": metrics,
        "data_sufficiency": "INSUFFICIENT",
        "generation_mode": "DETERMINISTIC_FALLBACK",
        "limitations": [
            "No uplift, profit or item margin is inferred from payment totals.",
            "Merchant approval and separate activation remain mandatory.",
        ],
    }
    if not merchant_settings or not metrics["successful_count"]:
        return result
    settings = MerchantPromotion.model_validate(merchant_settings)
    rule = settings.rule_parameters
    name = (
        f"Nth-payment reward (N={rule['n']})"
        if settings.type == "NTH_PAYMENT"
        else "Collection-threshold reward"
    )
    result["suggested_action"] = {
        "name": name,
        "type": settings.type,
        "rule_parameters": rule,
        "reward_cost_paise": settings.reward_cost_paise,
        "budget_cap_paise": settings.budget_cap_paise,
        "starts_at": data.now.isoformat(),
        "ends_at": (data.now + timedelta(days=settings.duration_days)).isoformat(),
    }
    result["data_sufficiency"] = "SUFFICIENT"
    result["explanation"] = (
        f"The selected period contains {metrics['successful_count']} successful recorded payment(s). "
        "This suggestion copies your configured rule, fixed reward cost and spending cap. "
        "Sufficiency here means the configured rule can be proposed; it does not establish campaign effectiveness."
    )
    if any(
        "partial" in warning or "unknown" in warning for warning in metrics["warnings"]
    ):
        result["limitations"].append(
            "Coverage is incomplete; the suggestion is not a seasonal or causal growth prediction."
        )
    return result
