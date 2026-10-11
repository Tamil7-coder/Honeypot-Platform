"""multi-honeypot support: add command_metadata for structured protocol data

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("commands", sa.Column("command_metadata", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("commands", "command_metadata")
