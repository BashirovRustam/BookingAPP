from typing import List, Optional

from sqlalchemy import Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.Room.models import Room


class Hotel(Base):
    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str] = mapped_column(String(256), nullable=False)
    services: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    room_quality: Mapped[Optional[str]] = mapped_column(String(64))
    image_id: Mapped[Optional[int]] = mapped_column(Integer)

    rooms: Mapped[List["Room"]] = relationship(
        back_populates="hotel",
        cascade="all, delete-orphan",
    )


