from fastapi import Query
from pydantic import BaseModel


class HotelFilter(BaseModel):
    location: str | None = None


def get_hotel_filter(
    location: str | None = Query(None, description="Filter by hotel location"),
) -> HotelFilter:
    return HotelFilter(location=location)


class RoomFilter(BaseModel):
    price_min: int | None = None
    price_max: int | None = None
