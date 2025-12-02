from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Date, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.User.models import User


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    price_per_day: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    totals_day: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="booking")
    rooms: Mapped[List["Room"]] = relationship(
        "Room",
        secondary="booking_rooms",
        back_populates="booking",
    )
    booking_rooms: Mapped[List["BookingRooms"]] = relationship(
        back_populates="booking",
        cascade="all, delete-orphan",
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
            # room.id может быть None, если объект ещё не сохранён
            return getattr(first_room, "id", None)
        return None


