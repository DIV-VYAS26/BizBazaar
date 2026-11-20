"""Durable mail work. Local outbox mode never contacts an SMTP server."""

import smtplib
import ssl
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.commerce import Customer, EmailOutbox, RateBucket
from app.db.models import Merchant
from app.services.credit import ledger
from app.services.mail import cipher, queue_email
from app.services.transactions import system_audit


def smtp_send(settings, row):
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = (
        settings.mail_from,
        row.recipient,
        row.subject,
    )
    message["Message-ID"] = f"<{row.id}@bizbazaar>"
    message.set_content(cipher(settings).decrypt(row.encrypted_body.encode()).decode())
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.ehlo()
        if settings.smtp_starttls:
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        server.send_message(message)


def deliver_one(engine, settings, sender=smtp_send):
    if settings.mail_delivery_mode != "smtp":
        return "PREVIEW_ONLY"
    now = datetime.now(UTC)
    with Session(engine, expire_on_commit=False) as db:
        # Lease via next_attempt_at permits recovery after a worker crash. SMTP is at-least-once.
        row = db.scalar(
            select(EmailOutbox)
            .where(
                EmailOutbox.status.in_(["QUEUED", "RETRY", "SENDING"]),
                EmailOutbox.next_attempt_at <= now,
            )
            .order_by(EmailOutbox.created_at, EmailOutbox.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if row is None:
            return "IDLE"
        if row.attempts >= 5:
            row.status = "FAILED"
            db.commit()
            return "FAILED"
        row.status, row.attempts = "SENDING", row.attempts + 1
        row.next_attempt_at = now + timedelta(minutes=5)
        row_id, merchant_id = row.id, row.merchant_id
        db.commit()
    with Session(engine, expire_on_commit=False) as db:
        # Merchant lock serializes delivery with consent/email changes and cooldown updates.
        db.scalar(select(Merchant).where(Merchant.id == merchant_id).with_for_update())
        row = db.scalar(select(EmailOutbox).where(EmailOutbox.id == row_id).with_for_update())
        customer = db.get(Customer, row.customer_id) if row.customer_id else None
        if row.kind == "MARKETING" and (
            not settings.marketing_delivery_enabled
            or not customer
            or not customer.marketing_opt_in
            or not customer.consent_at
            or customer.email != row.recipient
            or (customer.last_marketing_at and customer.last_marketing_at > now - timedelta(days=7))
        ):
            row.status = "SUPPRESSED"
        elif customer and customer.email != row.recipient:
            row.status = "SUPPRESSED"
        else:
            try:
                sender(settings, row)
            except Exception:
                # SMTP errors may contain credentials or message text; do not persist them.
                row.status = "FAILED" if row.attempts >= 5 else "RETRY"
                row.next_attempt_at = now + timedelta(minutes=2**row.attempts)
            else:
                row.status, row.sent_at = "SENT", datetime.now(UTC)
                if row.kind == "MARKETING":
                    customer.last_marketing_at = row.sent_at
        system_audit(db, merchant_id, "MAIL_" + row.status, row.id, {"kind": row.kind})
        db.commit()
        return row.status


def queue_due_reminders(db, actor, settings):
    from app.core.security import lock_merchant

    lock_merchant(db, actor)
    merchant = db.get(Merchant, actor.merchant_id)
    from zoneinfo import ZoneInfo

    day = datetime.now(UTC).astimezone(ZoneInfo(merchant.timezone)).date()
    count = 0
    people = db.scalars(
        select(Customer)
        .where(Customer.merchant_id == actor.merchant_id, Customer.email.is_not(None))
        .order_by(Customer.id)
        .limit(100)
    ).all()
    for customer in people:
        key = f"due:{customer.id}:{day}"
        if db.scalar(select(EmailOutbox.id).where(EmailOutbox.dedup_key == key)):
            continue
        record = ledger(db, actor.merchant_id, customer.id)
        if record.overdue_paise <= 0:
            continue
        # A reminder is a transaction notice, separate from marketing consent.
        queue_email(
            db,
            settings,
            actor.merchant_id,
            customer.email,
            "Your credit record is due for review",
            f"Your recorded overdue balance is INR {record.overdue_paise // 100}."
            f"{record.overdue_paise % 100:02d}. "
            "Reply to the merchant if you disagree. This notice does not collect payment.",
            "DUE_REMINDER",
            key,
            customer.id,
        )
        count += 1
    system_audit(db, actor.merchant_id, "DUE_REMINDERS_QUEUED", uuid4(), {"count": count})
    db.commit()
    return count


def cleanup(engine):
    with Session(engine) as db:
        db.execute(delete(RateBucket).where(RateBucket.expires_at < datetime.now(UTC)))
        db.commit()


def main():
    import argparse
    import time

    from app.core.config import get_settings
    from app.db.session import get_engine

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings, engine = get_settings(), get_engine()
    while True:
        result = deliver_one(engine, settings)
        cleanup(engine)
        if args.once:
            print(result)
            return
        time.sleep(5 if result in {"PREVIEW_ONLY", "IDLE"} else 0.1)


if __name__ == "__main__":
    main()
