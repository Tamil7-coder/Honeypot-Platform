"""phase 3: add severity enum, attack_sessions.severity, and alerts table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    severity_enum = postgresql.ENUM("low", "medium", "high", "critical", name="severity_enum")
    severity_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "attack_sessions",
        sa.Column(
            "severity",
            postgresql.ENUM("low", "medium", "high", "critical", name="severity_enum", create_type=False),
            nullable=True,
        ),
    )
    op.create_index("ix_attack_sessions_severity", "attack_sessions", ["severity"])

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attack_sessions.id"), nullable=True),
        sa.Column(
            "severity",
            postgresql.ENUM("low", "medium", "high", "critical", name="severity_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source_ip", postgresql.INET(), nullable=True),
        sa.Column("email_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("email_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_attack_sessions_severity", table_name="attack_sessions")
    op.drop_column("attack_sessions", "severity")
    postgresql.ENUM(name="severity_enum").drop(op.get_bind(), checkfirst=True)
