"""Encrypt a local Compose PostgreSQL backup, or verify it in a new disposable database.

No restore command accepts an existing database name. The verification database is generated here.
"""

import argparse
import os
import subprocess
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 200 * 1024 * 1024


def run(arguments, data=None, service="db"):
    result = subprocess.run(
        ["docker-compose", "exec", "-T", service, *arguments],
        input=data,
        capture_output=True,
        cwd=ROOT,
        timeout=120,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            "Database operation failed; credentials and SQL output were withheld"
        )
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "verify"])
    parser.add_argument("file", type=Path)
    parser.add_argument(
        "--test-source",
        action="store_true",
        help="Use the isolated test-db service and bizbazaar_test database",
    )
    args = parser.parse_args()
    service = "test-db" if args.test_source else "db"
    source = "bizbazaar_test" if args.test_source else "bizbazaar"
    values = dotenv_values(ROOT / ".env")
    key = os.environ.get("BACKUP_ENCRYPTION_KEY") or values.get("BACKUP_ENCRYPTION_KEY")
    if not key:
        raise SystemExit("Create the private BACKUP_ENCRYPTION_KEY first")
    cipher = Fernet(key.encode())
    if args.action == "backup":
        if args.file.exists():
            raise SystemExit("Refusing to overwrite an existing backup")
        # Local-only tool: production must configure its own scheduled backup provider.
        command = [
            "docker-compose",
            "exec",
            "-T",
            service,
            "pg_dump",
            "-U",
            "bizbazaar",
            "-d",
            source,
            "--format=custom",
            "--no-owner",
            "--no-acl",
        ]
        process = subprocess.Popen(
            command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        data = bytearray()
        try:
            while chunk := process.stdout.read(65536):
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise RuntimeError("Backup exceeds the local 200 MiB limit")
            if process.wait(timeout=120):
                raise RuntimeError("Backup failed")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
        args.file.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(args.file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(cipher.encrypt(bytes(data)))
        print("Encrypted backup created. Keep the private key separately.")
    else:
        if args.file.stat().st_size > MAX_BYTES * 2:
            raise SystemExit("Backup exceeds the verification size limit")
        data = cipher.decrypt(args.file.read_bytes())
        name = "restore_" + uuid4().hex + "_test"
        run(["createdb", "-U", "bizbazaar", name], service=service)
        try:
            run(
                [
                    "pg_restore",
                    "-U",
                    "bizbazaar",
                    "-d",
                    name,
                    "--no-owner",
                    "--no-acl",
                    "--exit-on-error",
                ],
                data,
                service=service,
            )
            result = (
                run(
                    [
                        "psql",
                        "-U",
                        "bizbazaar",
                        "-d",
                        name,
                        "-At",
                        "-v",
                        "ON_ERROR_STOP=1",
                        "-c",
                        (
                            "SELECT count(*) FROM alembic_version; SELECT count(*) FROM merchants; "
                            "SELECT count(*) FROM sales; SELECT count(*) FROM credit_events;"
                        ),
                    ],
                    service=service,
                )
                .decode()
                .splitlines()
            )
            if not result or result[0] != "1":
                raise RuntimeError("Restored migration metadata was not valid")
            print(
                f"Restore verified: {result[1]} merchants, {result[2]} sales, "
                f"{result[3]} credit events in a disposable database."
            )
        finally:
            run(["dropdb", "-U", "bizbazaar", "--if-exists", name], service=service)


if __name__ == "__main__":
    main()
