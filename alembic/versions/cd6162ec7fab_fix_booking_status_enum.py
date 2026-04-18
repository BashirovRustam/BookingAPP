"""fix_booking_status_enum

Revision ID: cd6162ec7fab
Revises: fadb7336fb1a
Create Date: 2025-12-11 20:25:24.068367

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "cd6162ec7fab"
down_revision: Union[str, Sequence[str], None] = "fadb7336fb1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("ALTER TABLE bookings ALTER COLUMN status TYPE VARCHAR(20)")
    op.execute("DROP TYPE IF EXISTS bookingstatus")
    op.execute(
        "CREATE TYPE bookingstatus AS ENUM ('pending', 'confirmed', 'cancelled')"
    )
    op.execute(
        "ALTER TABLE bookings ALTER COLUMN status TYPE bookingstatus USING LOWER(status)::bookingstatus"
    )
    op.execute("ALTER TABLE bookings ALTER COLUMN status SET DEFAULT 'pending'")


def downgrade():
    op.execute("ALTER TABLE bookings ALTER COLUMN status TYPE VARCHAR(20)")
    op.execute("DROP TYPE IF EXISTS bookingstatus")
    op.execute(
        "CREATE TYPE bookingstatus AS ENUM ('PENDING', 'CONFIRMED', 'CANCELLED')"
    )
    op.execute(
        "ALTER TABLE bookings ALTER COLUMN status TYPE bookingstatus USING UPPER(status)::bookingstatus"
    )
