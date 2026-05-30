"""add PAP fleet SRP config keys

Revision ID: 0004srp
Revises: 0003srp
Create Date: 2026-05-18
"""

import sqlalchemy as sa
from alembic import op
from datetime import UTC, datetime

revision = "0004srp"
down_revision = "0003srp"
branch_labels = None
depends_on = None

_NOW = datetime.now(UTC).isoformat()

_NEW_KEYS = [
    {"key": "pap_coefficient",    "value": "1.0",   "updated_at": _NOW},
    {"key": "pap_enabled",        "value": "true",  "updated_at": _NOW},
    {"key": "pap_min_loss_value", "value": "0",     "updated_at": _NOW},
    {"key": "pap_full_loss",      "value": "false",  "updated_at": _NOW},
]

_TABLE = sa.table(
    "srp_configs",
    sa.column("key",        sa.String),
    sa.column("value",      sa.Text),
    sa.column("updated_at", sa.DateTime),
)


def upgrade() -> None:
    op.bulk_insert(_TABLE, _NEW_KEYS)


def downgrade() -> None:
    keys = [r["key"] for r in _NEW_KEYS]
    placeholders = ", ".join(f"'{k}'" for k in keys)
    op.execute(f"DELETE FROM srp_configs WHERE key IN ({placeholders})")
