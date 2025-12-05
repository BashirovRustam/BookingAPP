from datetime import date
from pydantic import BaseModel, EmailStr, Field


class BookingInProfile(BaseModel):
    room_id: int
    room_name: str
    start_date: date
    end_date: date


class MeResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    bookings: list[BookingInProfile]
