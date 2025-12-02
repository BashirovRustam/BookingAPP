"""Populate the Booking_DB with Kazakh-themed demo data."""

import asyncio
import random
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Sequence

from sqlalchemy import func, select

from app.Booking.models import Booking
from app.BookingRooms.models import BookingRooms  # noqa: F401 - ensures metadata
from app.Hotel.models import Hotel
from app.Room.models import Room
from app.User.models import User
from app.db.base import AsyncSessionFactory, init_models

KZ_HOTELS = [
    {
        "name": "Астана Премиум Кервансарай",
        "location": "Астана, бульвар Нуржол",
        "services": {"SPA": "хаммам и бассейн", "Трансфер": "аэропорт Нурсултан Назарбаев"},
        "room_quality": "премиум",
        "image_id": 501,
    },
    {
        "name": "Алматы Пик Плаза",
        "location": "Алматы, проспект Достык",
        "services": {"Гид": "по горам Иле Алатау", "Кофейня": "зерно из Жетысу"},
        "room_quality": "делюкс",
        "image_id": 502,
    },
    {
        "name": "Каспийская Ривьера",
        "location": "Актау, набережная 15-й мкр",
        "services": {"Пляж": "частный", "Катер": "прогулки по Каспию"},
        "room_quality": "курорт",
        "image_id": 503,
    },
    {
        "name": "Шымкент Жибек Жолы",
        "location": "Шымкент, улица Байдибек би",
        "services": {"Базар": "автобус к Самал", "Чайхана": "узбекская кухня"},
        "room_quality": "комфорт",
        "image_id": 504,
    },
]

KZ_ROOMS = [
    {
        "hotel_idx": 0,
        "name": "Люкс «Бәйтерек»",
        "descriptions": "Панорама на Есиль, дизайнерский юрточный декор.",
        "price_per_day": Decimal("88000.00"),
        "services": {"Wi-Fi": "гигабитный", "Сауна": "инфракрасная"},
        "quality": "люкс",
        "image_id": 601,
    },
    {
        "hotel_idx": 0,
        "name": "Номер «Expo»",
        "descriptions": "Минимализм, умный дом и арт об Expo-2017.",
        "price_per_day": Decimal("64000.00"),
        "services": {"VR-тур": "по павильонам EXPO", "Завтрак": "кулинария Акмола"},
        "quality": "бизнес",
        "image_id": 602,
    },
    {
        "hotel_idx": 1,
        "name": "Апартаменты «Алатау»",
        "descriptions": "Тёплые полы, камин BioLite и терраса с видом на горы.",
        "price_per_day": Decimal("72000.00"),
        "services": {"Ски-камеры": "Чимбулак", "Трансфер": "Медеу"},
        "quality": "комфорт",
        "image_id": 603,
    },
    {
        "hotel_idx": 1,
        "name": "Студия «Верный»",
        "descriptions": "Современный дизайн с акцентами Верного и арт Устемира.",
        "price_per_day": Decimal("56000.00"),
        "services": {"Бариста": "кофе на песке", "Велосипеды": "прокат"},
        "quality": "бизнес",
        "image_id": 604,
    },
    {
        "hotel_idx": 2,
        "name": "Сьют «Каспий»",
        "descriptions": "Панорамные окна на море, аква-сцена и лаунж зона.",
        "price_per_day": Decimal("68000.00"),
        "services": {"Катер": "до острова Каратон", "Шеф": "каспийские морепродукты"},
        "quality": "курорт",
        "image_id": 605,
    },
    {
        "hotel_idx": 2,
        "name": "Вилла «Желмая»",
        "descriptions": "Приватная терраса, тандыр и аперитивы с видом на закат.",
        "price_per_day": Decimal("95000.00"),
        "services": {"Йога": "на пляже", "SUP": "прокат досок"},
        "quality": "премиум",
        "image_id": 606,
    },
    {
        "hotel_idx": 3,
        "name": "Номер «Орда»",
        "descriptions": "Комнаты с резьбой Южного Казахстана и ароматным чаем.",
        "price_per_day": Decimal("43000.00"),
        "services": {"Экскурсия": "к Арыстан баб", "Табылдылық": "ужин дегустация"},
        "quality": "комфорт",
        "image_id": 607,
    },
    {
        "hotel_idx": 3,
        "name": "Семейный «Сайрам»",
        "descriptions": "Две спальни, детская юрта и интерактив о Шымкенте.",
        "price_per_day": Decimal("51000.00"),
        "services": {"Гид": "к ущелью Сайрам-Угам", "Транспорт": "кыз узату сервис"},
        "quality": "семейный",
        "image_id": 608,
    },
]

KZ_USERS: Sequence[tuple[str, str, str]] = [
    ("aida.seitova@travel.kz", "Аида", "Сеитова"),
    ("yerbol.akhmetov@travel.kz", "Ербол", "Ахметов"),
    ("madina.rakhimova@travel.kz", "Мадина", "Рахимова"),
    ("daulet.tulepov@travel.kz", "Даулет", "Тулепов"),
    ("aliya.bakyt@travel.kz", "Алия", "Бакыт"),
    ("nurlan.tasmagambet@travel.kz", "Нурлан", "Тасмагамбет"),
    ("saltanat.kairat@travel.kz", "Салтанат", "Кайрат"),
    ("assel.kudaibergen@travel.kz", "Асель", "Кудайберген"),
    ("dias.omarov@travel.kz", "Диас", "Омаров"),
    ("zhanel.askarova@travel.kz", "Жанель", "Аскарова"),
    ("rustem.kyrykbai@travel.kz", "Рустем", "Кырыкбай"),
    ("gulshat.mukanova@travel.kz", "Гульшат", "Муканова"),
    ("sanzhar.khamitov@travel.kz", "Санжар", "Хамитов"),
    ("arina.zhumadilova@travel.kz", "Арина", "Жумадилова"),
    ("adil.saparov@travel.kz", "Адиль", "Сапаров"),
    ("botagoz.ismetova@travel.kz", "Ботагоз", "Исметова"),
    ("roma.nagmetov@travel.kz", "Роман", "Нагметов"),
    ("dinara.tursyn@travel.kz", "Динара", "Турсын"),
    ("timur.yermek@travel.kz", "Тимур", "Ермеков"),
    ("karina.serik@travel.kz", "Карина", "Серикбаева"),
]


async def ensure_hotels(session) -> List[Hotel]:
    hotels_count = await session.scalar(select(func.count(Hotel.id)))
    if hotels_count:
        result = await session.scalars(select(Hotel))
        return list(result)

    hotel_entities = [Hotel(**payload) for payload in KZ_HOTELS]
    session.add_all(hotel_entities)
    await session.flush()
    return hotel_entities


async def ensure_rooms(session, hotels: Sequence[Hotel]) -> List[Room]:
    rooms_count = await session.scalar(select(func.count(Room.id)))
    if rooms_count:
        result = await session.scalars(select(Room))
        return list(result)

    room_entities: List[Room] = []
    for payload in KZ_ROOMS:
        hotel = hotels[payload["hotel_idx"]]
        room = Room(hotel_id=hotel.id, **{k: v for k, v in payload.items() if k != "hotel_idx"})
        room_entities.append(room)
    session.add_all(room_entities)
    await session.flush()
    return room_entities


async def ensure_users(session) -> List[User]:
    users_count = await session.scalar(select(func.count(User.id)))
    if users_count:
        result = await session.scalars(select(User))
        return list(result)

    user_entities = [
        User(
            email=email,
            hash_password=f"hash_{idx:04d}",
            first_name=first,
            last_name=last,
        )
        for idx, (email, first, last) in enumerate(KZ_USERS, start=1)
    ]
    session.add_all(user_entities)
    await session.flush()
    return user_entities


async def seed_bookings(session, users: Sequence[User], rooms: Sequence[Room], min_bookings: int) -> int:
    existing = await session.scalar(select(func.count(Booking.id)))
    if existing and existing >= min_bookings:
        return 0

    random.seed(2024)
    start_date = date(2024, 1, 1)
    bookings_to_create: List[Booking] = []

    for _ in range(min_bookings):
        guest = random.choice(users)
        room = random.choice(rooms)
        offset_days = random.randint(0, 540)
        stay_length = random.randint(1, 12)
        arrival = start_date + timedelta(days=offset_days)
        departure = arrival + timedelta(days=stay_length)
        total_cost = room.price_per_day * Decimal(stay_length)

        booking = Booking(
            date_from=arrival,
            date_to=departure,
            price_per_day=room.price_per_day,
            totals_day=stay_length,
            total_cost=total_cost,
            user_id=guest.id,
        )
        booking.rooms.append(room)
        bookings_to_create.append(booking)

    session.add_all(bookings_to_create)
    await session.commit()
    return len(bookings_to_create)


async def seed_database(min_bookings: int = 200) -> None:
    async with AsyncSessionFactory() as session:
        hotels = await ensure_hotels(session)
        rooms = await ensure_rooms(session, hotels)
        users = await ensure_users(session)
        created = await seed_bookings(session, users, rooms, min_bookings)
        if created:
            print(f"Создано {created} бронирований с казахстанскими сценариями.")
        else:
            print("Минимальное количество бронирований уже есть, наполнение не потребовалось.")


async def main() -> None:
    await init_models()
    await seed_database()


if __name__ == "__main__":
    asyncio.run(main())

