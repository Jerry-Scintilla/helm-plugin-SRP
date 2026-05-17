"""add full_loss config key

Revision ID: 0003srp
Revises: 0002srp
Create Date: 2026-05-18
"""

import sqlalchemy as sa
from alembic import op
from datetime import UTC, datetime

revision = "0003srp"
down_revision = "0002srp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.bulk_insert(
        sa.table(
            "srp_configs",
            sa.column("key", sa.String),
            sa.column("value", sa.Text),
            sa.column("updated_at", sa.DateTime),
        ),
        [{"key": "full_loss", "value": "false", "updated_at": datetime.now(UTC).isoformat()}],
    )


def downgrade() -> None:
    op.execute("DELETE FROM srp_configs WHERE key = 'full_loss'")
