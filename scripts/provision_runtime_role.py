"""Prepare a least-privilege database role after migrations. Run explicitly during launch setup."""

import os

import psycopg
from app.core.config import get_settings
from psycopg import sql


def main():
    settings = get_settings()
    password = os.environ.get("RUNTIME_DB_PASSWORD", "")
    if len(password) < 32:
        raise SystemExit(
            "Set RUNTIME_DB_PASSWORD to a private random value of at least 32 characters"
        )
    url = settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        if not cursor.execute(
            "SELECT 1 FROM pg_roles WHERE rolname='bizbazaar_runtime'"
        ).fetchone():
            cursor.execute(
                "CREATE ROLE bizbazaar_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS"
            )
        cursor.execute(
            sql.SQL("ALTER ROLE bizbazaar_runtime PASSWORD {}").format(
                sql.Literal(password)
            )
        )
        cursor.execute("GRANT USAGE ON SCHEMA public TO bizbazaar_runtime")
        cursor.execute(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bizbazaar_runtime"
        )
        cursor.execute(
            "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bizbazaar_runtime"
        )
        cursor.execute("REVOKE ALL ON alembic_version FROM bizbazaar_runtime")
        for table in [
            "audit_logs",
            "credit_events",
            "credit_acknowledgements",
            "loyalty_events",
            "sale_lines",
            "business_requests",
        ]:
            cursor.execute(
                sql.SQL(
                    "REVOKE UPDATE, DELETE, TRUNCATE ON {} FROM bizbazaar_runtime"
                ).format(sql.Identifier(table))
            )
    print("Runtime role prepared; its password was not printed.")


if __name__ == "__main__":
    main()
