"""initial schema: roles, users, honeypots, attack sessions, login attempts, commands, audit logs

Revision ID: 0001
Revises:
Create Date: 2026-07-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    role_enum = postgresql.ENUM("admin", "analyst", "viewer", name="role_name_enum")
    role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", postgresql.ENUM("admin", "analyst", "viewer", name="role_name_enum", create_type=False), nullable=False, unique=True),
        sa.Column("description", sa.String(length=255), nullable=True),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "honeypots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("honeypot_type", sa.String(length=50), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "attack_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("honeypot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("honeypots.id"), nullable=False),
        sa.Column("session_ref", sa.String(length=128), nullable=False),
        sa.Column("source_ip", postgresql.INET(), nullable=False),
        sa.Column("source_port", sa.Integer(), nullable=True),
        sa.Column("destination_port", sa.Integer(), nullable=True),
        sa.Column("protocol", sa.String(length=20), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_attack_sessions_source_ip", "attack_sessions", ["source_ip"])
    op.create_index("ix_attack_sessions_country_code", "attack_sessions", ["country_code"])
    op.create_index("ix_attack_sessions_started_at", "attack_sessions", ["started_at"])
    op.create_index("ix_attack_sessions_source_ip_started_at", "attack_sessions", ["source_ip", "started_at"])
    op.create_unique_constraint("uq_attack_sessions_session_ref", "attack_sessions", ["session_ref"])

    op.create_table(
        "login_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attack_sessions.id"), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_login_attempts_username", "login_attempts", ["username"])
    op.create_index("ix_login_attempts_password", "login_attempts", ["password"])

    op.create_table(
        "commands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attack_sessions.id"), nullable=False),
        sa.Column("command_text", sa.Text(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed default roles
    op.execute("INSERT INTO roles (name, description) VALUES ('admin', 'Full platform access')")
    op.execute("INSERT INTO roles (name, description) VALUES ('analyst', 'Read/write access to attack data and reports')")
    op.execute("INSERT INTO roles (name, description) VALUES ('viewer', 'Read-only dashboard access')")


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("commands")
    op.drop_table("login_attempts")
    op.drop_table("attack_sessions")
    op.drop_table("honeypots")
    op.drop_table("users")
    op.drop_table("roles")
    postgresql.ENUM(name="role_name_enum").drop(op.get_bind(), checkfirst=True)
