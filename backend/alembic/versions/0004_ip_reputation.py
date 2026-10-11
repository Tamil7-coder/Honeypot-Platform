"""phase 6: add ip_reputation table for threat intelligence caching

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ip_reputation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ip_address", postgresql.INET(), nullable=False, unique=True),
        sa.Column("abuseipdb_data", postgresql.JSONB(), nullable=True),
        sa.Column("virustotal_data", postgresql.JSONB(), nullable=True),
        sa.Column("otx_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "threat_level",
            postgresql.ENUM("low", "medium", "high", "critical", name="severity_enum", create_type=False),
            nullable=True,
        ),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ip_reputation_ip_address", "ip_reputation", ["ip_address"])


def downgrade() -> None:
    op.drop_index("ix_ip_reputation_ip_address", table_name="ip_reputation")
    op.drop_table("ip_reputation")
