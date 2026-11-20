"""Local-only provisioning; never expose this functionality as a public signup endpoint."""

import argparse
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import digest
from app.db.models import DemoSession, Merchant, MerchantSettings
from app.db.session import get_engine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["create-demo-session"])
    parser.add_argument("--merchant-name", required=True)
    args = parser.parse_args()
    settings = get_settings()
    if not settings.demo_enabled or settings.app_env != "local":
        parser.error("Demo provisioning requires APP_ENV=local and DEMO_ENABLED=true")
    if not 1 <= len(args.merchant_name) <= 120:
        parser.error("Merchant name must be 1-120 characters")
    with Session(get_engine()) as db:
        merchant = db.scalar(select(Merchant).where(Merchant.name == args.merchant_name))
        if merchant is None:
            merchant = Merchant(name=args.merchant_name)
            db.add(merchant)
            db.flush()
            # Explicit local-demo settings; no AI-generated financial parameters.
            db.add(
                MerchantSettings(
                    merchant_id=merchant.id,
                    promotion={
                        "type": "NTH_PAYMENT",
                        "rule_parameters": {"n": 3},
                        "reward_cost_paise": 10000,
                        "budget_cap_paise": 10000,
                        "duration_days": 1,
                    },
                )
            )
        token = secrets.token_urlsafe(32)
        db.add(
            DemoSession(
                merchant_id=merchant.id,
                token_hash=digest(token),
                csrf_hash=digest(secrets.token_urlsafe(32)),
                expires_at=datetime.now(UTC) + timedelta(hours=settings.session_hours),
            )
        )
        db.commit()
        print(f"Merchant: {merchant.id}")
        print("One-time demo credential (keep private; exchanged for browser cookies):")
        print(token)


if __name__ == "__main__":
    main()
