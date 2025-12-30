from pydantic import BaseModel, EmailStr


class SendReceiptPayload(BaseModel):
    """Payload для отправки в Notification Service"""

    # Информация о платеже
    payment_id: str
    order_id: str
    capture_id: str
    amount: str
    currency: str

    # Информация о пользователе
    user_email: EmailStr
    user_name: str | None = None

    description: str
    created_at: str
    completed_at: str

    # Дополнительно
    transaction_fee: str | None = None
