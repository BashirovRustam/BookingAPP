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

