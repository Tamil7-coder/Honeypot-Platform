"""phase 7: add risk_score to attack_sessions

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("attack_sessions", sa.Column("risk_score", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("attack_sessions", "risk_score")
