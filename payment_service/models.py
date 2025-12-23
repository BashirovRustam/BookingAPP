import uuid
from datetime import datetime, timezone
import enum
from typing import Optional

from sqlalchemy import String, Float, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, declarative_base

Base = declarative_base()


class PaymentStatus(str, enum.Enum):
    pending = "pending"  # Ожидает оплаты
    success = "success"  # Оплата успешна
    failed = "failed"  # Ошибка платежа
    cancelled = "cancelled"  # Платёж отменён


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    booking_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Float, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending
    )
    transaction_id: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
