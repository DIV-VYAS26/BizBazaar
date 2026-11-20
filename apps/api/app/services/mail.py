from cryptography.fernet import Fernet

from app.core.errors import ApiError
from app.db.commerce import EmailOutbox


def cipher(settings):
    if settings.mail_encryption_key is None:
        raise ApiError(503, "MAIL_NOT_CONFIGURED", "Account mail storage is not configured")
    return Fernet(settings.mail_encryption_key.get_secret_value().encode())


def queue_email(
    db, settings, merchant_id, recipient, subject, body, kind, dedup_key, customer_id=None
):
    row = EmailOutbox(
        merchant_id=merchant_id,
        customer_id=customer_id,
        recipient=recipient,
        subject=subject,
        encrypted_body=cipher(settings).encrypt(body.encode()).decode(),
        kind=kind,
        dedup_key=dedup_key,
    )
    db.add(row)
    return row
