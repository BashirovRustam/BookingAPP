from datetime import date
from typing import TYPE_CHECKING, List, Optional
from enum import Enum

from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SqlEnum

from app.db.base import Base

if TYPE_CHECKING:
    from app.User.models import User
    from app.Room.models import Room
    from app.BookingRooms.models import BookingRooms


class BookingStatus(str, Enum):
    PENDING = "PENDING"  # Ожидает подтверждения
    CONFIRMED = "CONFIRMED"  # Подтверждено
    CANCELLED = "CANCELLED"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    price_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    totals_day: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        SqlEnum(BookingStatus, native_enum=True, name="bookingstatus"),
        default=BookingStatus.PENDING,
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="booking")
    rooms: Mapped[List["Room"]] = relationship(
        "Room",
        secondary="booking_rooms",
        back_populates="booking",
        overlaps="booking_rooms",
    )
    booking_rooms: Mapped[List["BookingRooms"]] = relationship(
        back_populates="booking",
        cascade="all, delete-orphan",
        overlaps="rooms",
    )

    def __str__(self) -> str:
        return f"{self.user} бронировал  {self.rooms} "

    @property
    def room_id(self) -> Optional[int]:
        """
        Удобное свойство для схем ответов: возвращает ID первой связанной комнаты.
        """

        if self.booking_rooms:
            return self.booking_rooms[0].room_id
        if self.rooms:
            first_room = self.rooms[0]
            return getattr(first_room, "id", None)
        return None
