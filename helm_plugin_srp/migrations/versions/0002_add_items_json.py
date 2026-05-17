"""add items_json to srp_requests

Revision ID: 0002srp
Revises: 0001srp
Create Date: 2026-05-18
"""

import sqlalchemy as sa
from alembic import op

revision = "0002srp"
down_revision = "0001srp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "srp_requests",
        sa.Column("items_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("srp_requests", "items_json")
