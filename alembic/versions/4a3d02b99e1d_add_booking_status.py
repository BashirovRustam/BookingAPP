"""Add status column to bookings

Revision ID: fadb7336fb1a
Revises: None
Create Date: 2025-12-11 19:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "fadb7336fb1a"
down_revision = None  # <- первая миграция
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Создаём ENUM type в PostgreSQL
    booking_status_enum = sa.Enum(
        "pending", "confirmed", "cancelled", name="bookingstatus"
    )
    booking_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Добавляем колонку status с типом ENUM
    op.add_column(
        "bookings",
        sa.Column(
            "status", booking_status_enum, nullable=False, server_default="pending"
        ),
    )


def downgrade() -> None:
    # 1. Удаляем колонку
    op.drop_column("bookings", "status")

    # 2. Удаляем ENUM type
    booking_status_enum = sa.Enum(
        "pending", "confirmed", "cancelled", name="bookingstatus"
    )
    booking_status_enum.drop(op.get_bind(), checkfirst=True)
