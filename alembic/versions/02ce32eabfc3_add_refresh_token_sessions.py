"""add_refresh_token_sessions

Revision ID: 02ce32eabfc3
Revises: cd6162ec7fab
Create Date: 2025-12-14 19:05:32.580096
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "02ce32eabfc3"
down_revision: Union[str, Sequence[str], None] = "cd6162ec7fab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add refresh_token_sessions table."""
    op.create_table(
        "refresh_token_sessions",
        sa.Column("jti", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index(
        op.f("ix_refresh_token_sessions_expires_at"),
        "refresh_token_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_token_sessions_revoked"),
        "refresh_token_sessions",
        ["revoked"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_token_sessions_user_id"),
        "refresh_token_sessions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema: drop refresh_token_sessions table."""
    op.drop_index(
        op.f("ix_refresh_token_sessions_user_id"), table_name="refresh_token_sessions"
    )
    op.drop_index(
        op.f("ix_refresh_token_sessions_revoked"), table_name="refresh_token_sessions"
    )
    op.drop_index(
        op.f("ix_refresh_token_sessions_expires_at"),
        table_name="refresh_token_sessions",
    )
    op.drop_table("refresh_token_sessions")
