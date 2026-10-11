"""phase 2: add full_name and is_email_verified to users

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add as nullable first so existing rows don't fail the constraint...
    op.add_column("users", sa.Column("full_name", sa.String(length=128), nullable=True))
    op.add_column(
        "users", sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.false())
    )

    # ...backfill existing rows (full_name defaults to username so nothing is left blank)...
    op.execute("UPDATE users SET full_name = username WHERE full_name IS NULL")

    # ...then enforce NOT NULL now that every row has a value.
    op.alter_column("users", "full_name", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "is_email_verified")
    op.drop_column("users", "full_name")
