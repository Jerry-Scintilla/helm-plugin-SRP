"""initial srp tables

Revision ID: 0001srp
Revises:
Create Date: 2026-05-16
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "0001srp"
down_revision = None
branch_labels = ("srp",)
depends_on = None


def upgrade() -> None:
    # srp_status enum
    op.execute("CREATE TYPE srp_status AS ENUM ('pending', 'approved', 'rejected', 'paid')")

    op.create_table(
        "srp_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("character_id", sa.BigInteger(), nullable=False),
        sa.Column("character_name", sa.String(128), nullable=False),
        sa.Column("killmail_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("killmail_hash", sa.String(64), nullable=False),
        sa.Column("zkb_url", sa.Text(), nullable=False),
        sa.Column("ship_type_id", sa.Integer(), nullable=False),
        sa.Column("ship_name", sa.String(256), nullable=False, server_default=""),
        sa.Column("loss_value_raw", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("calculated_value", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.Enum("pending", "approved", "rejected", "paid", name="srp_status"), nullable=False, server_default="pending"),
        sa.Column("fleet_action_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("officer_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_srp_requests_user_id",        "srp_requests", ["user_id"])
    op.create_index("ix_srp_requests_character_id",   "srp_requests", ["character_id"])
    op.create_index("ix_srp_requests_killmail_id",    "srp_requests", ["killmail_id"], unique=True)
    op.create_index("ix_srp_requests_status",         "srp_requests", ["status"])
    op.create_index("ix_srp_requests_fleet_action_id","srp_requests", ["fleet_action_id"])
    op.create_index("ix_srp_requests_created_at",     "srp_requests", ["created_at"])

    op.create_table(
        "srp_configs",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 写入默认配置
    from datetime import UTC, datetime
    now_str = datetime.now(UTC).isoformat()
    defaults = [
        ("price_region_id",     "10000002"),
        ("price_order_type",    "buy"),
        ("coefficient",         "1.0"),
        ("enabled",             "true"),
        ("min_loss_value",      "0"),
        ("eligible_ship_groups","[]"),
    ]
    op.bulk_insert(
        sa.table(
            "srp_configs",
            sa.column("key", sa.String),
            sa.column("value", sa.Text),
            sa.column("updated_at", sa.DateTime),
        ),
        [{"key": k, "value": v, "updated_at": now_str} for k, v in defaults],
    )


def downgrade() -> None:
    op.drop_table("srp_configs")
    op.drop_table("srp_requests")
    op.execute("DROP TYPE IF EXISTS srp_status")
