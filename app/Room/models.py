from typing import List, Optional

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    descriptions: Mapped[Optional[str]] = mapped_column(String(512))
    price_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    services: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    quality: Mapped[Optional[str]] = mapped_column(String(64))
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id"), nullable=False)
    image_id: Mapped[Optional[int]] = mapped_column(Integer)

    hotel: Mapped["Hotel"] = relationship(back_populates="rooms")
    booking_rooms: Mapped[List["BookingRooms"]] = relationship(
        back_populates="room",
        cascade="all, delete-orphan",
    )
    booking: Mapped[List["Booking"]] = relationship(
        "Booking",
        secondary="booking_rooms",
        back_populates="rooms",
    )


