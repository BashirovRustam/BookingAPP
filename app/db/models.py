"""
Этот файл обеспечивает импорт всех моделей для правильной регистрации в SQLAlchemy metadata.
Импорты здесь должны быть в правильном порядке чтобы избежать circular dependencies.
"""

# Import all models to ensure they're registered in SQLAlchemy's metadata
from app.Hotel.models import Hotel
from app.Room.models import Room
from app.BookingRooms.models import BookingRooms
from app.Booking.models import Booking

# Экспортируем все модели для удобства
__all__ = ["Hotel", "Room", "BookingRooms", "Booking"]
