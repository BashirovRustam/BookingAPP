from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from payment_service.models import PaymentStatus


class PaymentCreate(BaseModel):
    """Схема для создания платежа от монолита"""

    booking_id: int = Field(..., gt=0, description="ID бронирования из монолита")
    amount: int = Field(..., gt=0, description="Сумма в копейках")

    model_config = ConfigDict(
        json_schema_extra={"example": {"booking_id": 123, "amount": 9999}}
    )


class PaymentRead(BaseModel):
    """Схема для чтения платежа"""

    id: str
    booking_id: int
    amount: int
    status: PaymentStatus
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "booking_id": 123,
                "amount": 9999,
                "status": "success",
                "transaction_id": "txn_1234567890",
                "error_message": None,
                "created_at": "2024-12-22T10:30:00Z",
                "updated_at": "2024-12-22T10:35:00Z",
            }
        },
    )
