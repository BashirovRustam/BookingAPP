from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional


class BookingNotificationRequest(BaseModel):
    email: EmailStr
    booking_id: int
    hotel_name: str
    room_name: str
    check_in: date
    check_out: date
    total_price: float
    guest_name: Optional[str] = None
    confirm_url: Optional[str] = None


class NotificationResponse(BaseModel):
    status: str
    task_id: str
    message: str


class ReceiptPayload(BaseModel):
    """Схема данных для генерации и отправки чека"""

    # Информация о платеже
    payment_id: str  # UUID в виде строки
    order_id: str
    capture_id: str
    amount: str
    currency: str

    # Информация о пользователе
    user_email: EmailStr
    user_name: Optional[str] = None

    # Информация о заказе
    description: str
    created_at: str  # ISO format
    completed_at: str  # ISO format

    # Дополнительно
    transaction_fee: Optional[str] = None

