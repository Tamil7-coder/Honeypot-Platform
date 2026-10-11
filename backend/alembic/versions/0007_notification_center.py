"""phase 11: add is_read and dismissed_at to alerts

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("alerts", sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("alerts", "dismissed_at")
    op.drop_column("alerts", "is_read")
