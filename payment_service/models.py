import uuid
from datetime import datetime, timezone
import enum
from typing import Optional

from sqlalchemy import String, Float, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, declarative_base

Base = declarative_base()


class PaymentStatus(str, enum.Enum):
    created = "created"  # создан в системе
    pending = "pending"  # создан PayPal order
    completed = "completed"  # подтверждён webhook
    failed = "failed"  # ошибка платежа
    cancelled = "cancelled"  # платёж отменён
    refunded = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    booking_id: Mapped[int] = mapped_column(nullable=False, index=True)

    amount: Mapped[int] = mapped_column(
        nullable=False, comment="Сумма в минорных единицах (копейки)"
    )

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KZT")

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), nullable=False, default=PaymentStatus.created
    )

    # PayPal
    paypal_order_id: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, index=True
    )

    paypal_capture_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True)

    error_message: Mapped[Optional[str]] = mapped_column(String(255))

    # Email пользователя для отправки чека
    user_email: Mapped[Optional[str]] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
