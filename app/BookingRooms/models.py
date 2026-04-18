from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.Booking.models import Booking
    from app.Room.models import Room


class BookingRooms(Base):
    __tablename__ = "booking_rooms"

    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id"),
        primary_key=True,
    )
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id"),
        primary_key=True,
    )

    booking: Mapped["Booking"] = relationship(
        back_populates="booking_rooms", overlaps="rooms,booking"
    )
    room: Mapped["Room"] = relationship(
        back_populates="booking_rooms", overlaps="booking,rooms"
    )
