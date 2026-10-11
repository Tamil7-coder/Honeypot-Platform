"""phase 8: add files table for attack replay (downloads/uploads)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    direction_enum = postgresql.ENUM("download", "upload", name="file_direction_enum")
    direction_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attack_sessions.id"), nullable=False),
        sa.Column(
            "direction",
            postgresql.ENUM("download", "upload", name="file_direction_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_files_session_id", "files", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_files_session_id", table_name="files")
    op.drop_table("files")
    postgresql.ENUM(name="file_direction_enum").drop(op.get_bind(), checkfirst=True)
