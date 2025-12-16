from fastapi import Query
from pydantic import BaseModel


class HotelFilter(BaseModel):
    location: str | None = None


class RoomFilter(BaseModel):
    price_min: int | None = None
    price_max: int | None = None
