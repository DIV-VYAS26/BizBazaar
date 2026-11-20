"""Scope coverage declarations to datasets with or without simulated activity."""

import sqlalchemy as sa

from alembic import op

revision = "b2_coverage_scope"
down_revision = "6f5f4d2be035"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "coverage",
        sa.Column(
            "includes_simulated", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )
    op.drop_constraint("coverage_merchant_id_date_key", "coverage", type_="unique")
    op.create_unique_constraint(
        "uq_coverage_scope", "coverage", ["merchant_id", "date", "includes_simulated"]
    )


def downgrade():
    # Combining scopes would silently discard evidence; refuse ambiguous downgrades.
    connection = op.get_bind()
    duplicates = connection.execute(
        sa.text("SELECT 1 FROM coverage GROUP BY merchant_id, date HAVING count(*) > 1 LIMIT 1")
    ).first()
    if duplicates:
        raise RuntimeError("Resolve multiple coverage scopes before downgrading")
    op.drop_constraint("uq_coverage_scope", "coverage", type_="unique")
    op.drop_column("coverage", "includes_simulated")
    op.create_unique_constraint(
        "coverage_merchant_id_date_key", "coverage", ["merchant_id", "date"]
    )
