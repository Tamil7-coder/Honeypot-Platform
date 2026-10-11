"""add geolocation_data to ip_reputation (attacker address lookup)

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ip_reputation", sa.Column("geolocation_data", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("ip_reputation", "geolocation_data")
