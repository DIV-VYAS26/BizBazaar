import csv
import io
from datetime import UTC
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select

from app.core.errors import ApiError
from app.core.security import lock_merchant
from app.db.models import Transaction
from app.schemas.api import ImportReport, RowIssue, SimulationPayment
from app.services.metadata import invalidate_coverage
from app.services.transactions import atomic, audit

REQUIRED = {"transaction_id", "amount_paise", "currency", "timestamp", "status"}


def parse_csv(content, settings, merchant_id):
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ApiError(422, "INVALID_CSV", "CSV must use UTF-8 encoding") from None
    if "\x00" in decoded:
        raise ApiError(422, "INVALID_CSV", "CSV contains invalid characters")
    reader = csv.DictReader(io.StringIO(decoded), strict=True)
    try:
        headers = reader.fieldnames or []
        if set(headers) - {"merchant_id"} != REQUIRED or len(headers) != len(set(headers)):
            raise ApiError(422, "INVALID_HEADERS", "CSV headers do not match the contract")
        rows = []
        for number, row in enumerate(reader, start=2):
            if len(rows) >= settings.max_csv_rows:
                raise ApiError(413, "TOO_MANY_ROWS", "CSV exceeds the row limit")
            issue = None
            parsed = None
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("Row column count does not match the headers")
                if any(len(value) > settings.max_csv_field_chars for value in row.values()):
                    raise ValueError("CSV field exceeds the length limit")
                if "merchant_id" in row and UUID(row["merchant_id"]) != merchant_id:
                    raise ValueError("Row merchant does not match the current session")
                if row["currency"] != "INR":
                    raise ValueError("Only INR currency is supported")
                amount = row["amount_paise"]
                if not amount.isascii() or not amount.isdecimal() or len(amount) > 13:
                    raise ValueError("amount_paise must be a positive integer")
                parsed = SimulationPayment(
                    event_id="import",
                    transaction_id=row["transaction_id"],
                    amount_paise=int(amount),
                    timestamp=row["timestamp"],
                    status=row["status"],
                )
            except ValidationError as exc:
                field = str(exc.errors()[0]["loc"][0])
                issue = RowIssue(
                    row=number, kind="INVALID", field=field, reason="Invalid value for this field"
                )
            except (ValueError, TypeError) as exc:
                issue = RowIssue(row=number, kind="INVALID", reason=str(exc))
            rows.append((number, parsed, issue))
        return rows
    except (csv.Error, UnicodeError):
        raise ApiError(422, "INVALID_CSV", "CSV could not be parsed") from None


@atomic
def import_csv(db, actor, content, settings):
    rows = parse_csv(content, settings, actor.merchant_id)
    lock_merchant(db, actor)
    counts = {"imported": 0, "invalid": 0, "duplicates": 0, "conflicts": 0}
    issues = []
    for number, item, issue in rows:
        if issue:
            counts["invalid"] += 1
            issues.append(issue)
            continue
        existing = db.scalar(
            select(Transaction).where(
                Transaction.merchant_id == actor.merchant_id,
                Transaction.transaction_id == item.transaction_id,
            )
        )
        if existing:
            identical = (
                existing.source == "CSV"
                and existing.amount_paise == item.amount_paise
                and existing.timestamp == item.timestamp.astimezone(UTC)
                and existing.status == item.status.value
            )
            counts["duplicates" if identical else "conflicts"] += 1
            issues.append(
                RowIssue(
                    row=number,
                    kind="DUPLICATE" if identical else "CONFLICT",
                    reason="Transaction ID already recorded",
                )
            )
        else:
            db.add(
                Transaction(
                    merchant_id=actor.merchant_id,
                    transaction_id=item.transaction_id,
                    amount_paise=item.amount_paise,
                    timestamp=item.timestamp,
                    status=item.status.value,
                    source="CSV",
                    is_simulated=False,
                )
            )
            db.flush()
            counts["imported"] += 1
            invalidate_coverage(db, actor, item.timestamp, is_simulated=False)
    audit(db, actor, "CSV_IMPORTED", actor.merchant_id, counts)
    return ImportReport(**counts, issues=issues[:100], issues_truncated=len(issues) > 100)
