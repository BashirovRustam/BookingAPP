from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from payment_service.models import PaymentStatus


class PaymentCreate(BaseModel):
    """Схема для создания платежа от монолита"""

    booking_id: int = Field(..., gt=0, description="ID бронирования из монолита")
    amount: int = Field(..., gt=0, description="Сумма в минорных единицах (копейки)")
    currency: str = Field(default="USD", min_length=3, max_length=3)

    model_config = ConfigDict(
        json_schema_extra={"example": {"booking_id": 123, "amount": 9999}}
    )


class PaymentRead(BaseModel):
    id: str
    booking_id: int
    amount: int
    currency: str
    status: PaymentStatus
    paypal_order_id: Optional[str] = None
    paypal_capture_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = dict(from_attributes=True)


class PaymentCreateResponse(BaseModel):
    id: str
    booking_id: int
    amount: int
    currency: str
    status: PaymentStatus
    paypal_order_id: str
    approval_url: str
    created_at: datetime
