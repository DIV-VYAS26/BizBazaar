"""Create private local development keys without printing or overwriting existing values."""

import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

root = Path(__file__).resolve().parents[1]
target = root / ".env"
existing = (
    target.read_text() if target.exists() else (root / ".env.example").read_text()
)
keys = {
    line.split("=", 1)[0]
    for line in existing.splitlines()
    if "=" in line and not line.startswith("#")
}
additions = []
for name in ["MAIL_ENCRYPTION_KEY", "BACKUP_ENCRYPTION_KEY", "METRICS_TOKEN"]:
    if name not in keys:
        value = (
            Fernet.generate_key().decode()
            if name.endswith("ENCRYPTION_KEY")
            else secrets.token_urlsafe(32)
        )
        additions.append(f"{name}={value}")
target.write_text(existing.rstrip() + "\n" + "\n".join(additions) + "\n")
os.chmod(target, 0o600)
print("Local configuration is ready; private keys were not printed.")
