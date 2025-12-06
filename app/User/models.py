import enum
from typing import List

from sqlalchemy import Integer, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RolesEnum(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    hash_password: Mapped[str] = mapped_column(String(256), nullable=False)
    first_name: Mapped[str] = mapped_column(String(64), nullable=False)
    last_name: Mapped[str] = mapped_column(String(64), nullable=False)

    booking: Mapped[List["Booking"]] = relationship(back_populates="user")
    role: Mapped[RolesEnum] = mapped_column(
        Enum(RolesEnum), default=RolesEnum.USER, nullable=False
    )
    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"
