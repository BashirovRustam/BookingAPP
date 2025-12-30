from pydantic import BaseModel, EmailStr
from datetime import datetime
from decimal import Decimal


class SendReceiptPayload(BaseModel):
    """Payload для отправки в Notification Service"""

    # Информация о платеже
    payment_id: int
    order_id: str
    capture_id: str
    amount: str  # Передаём как строку для избежания проблем с JSON
    currency: str

    # Информация о пользователе
    user_email: EmailStr
    user_name: str | None = None

    # Информация о заказе/продукте
    description: str
    created_at: str  # ISO format
    completed_at: str  # ISO format

    # Дополнительно
    transaction_fee: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "payment_id": 123,
                "order_id": "ORDER-123ABC",
                "capture_id": "CAPTURE-456DEF",
                "amount": "99.99",
                "currency": "USD",
                "user_email": "user@example.com",
                "user_name": "John Doe",
                "description": "Premium subscription",
                "created_at": "2025-01-01T10:00:00",
                "completed_at": "2025-01-01T10:05:00",
            }
        }
