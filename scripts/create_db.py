"""Скрипт для наполнения базы данных Postgres в Docker контейнере."""

import asyncio
import random
from datetime import date, timedelta
from typing import List

from sqlalchemy import func, select

from app.Booking.models import Booking, BookingStatus
from app.BookingRooms.models import BookingRooms
from app.Hotel.models import Hotel
from app.Room.models import Room
from app.User.models import User, RolesEnum
from app.User.User_auth.security import hash_password
from app.db.base import AsyncSessionFactory, init_models

# Данные для отелей (30 отелей)
KZ_HOTELS = [
    {
        "name": "Астана Премиум Кервансарай",
        "location": "Астана, бульвар Нуржол",
        "services": {
            "SPA": "хаммам и бассейн",
            "Трансфер": "аэропорт Нурсултан Назарбаев",
        },
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
    {
        "name": "Караганда Бизнес Центр",
        "location": "Караганда, проспект Бухар жырау",
        "services": {"Конференц-зал": "на 200 человек", "Парковка": "подземная"},
        "room_quality": "бизнес",
        "image_id": 505,
    },
    {
        "name": "Павлодар Ертіс Гранд",
        "location": "Павлодар, набережная Иртыша",
        "services": {
            "Ресторан": "европейская кухня",
            "Фитнес": "современное оборудование",
        },
        "room_quality": "комфорт",
        "image_id": 506,
    },
    {
        "name": "Усть-Каменогорск Алтай Резорт",
        "location": "Усть-Каменогорск, предгорье Алтая",
        "services": {"Туризм": "походы в горы", "Рыбалка": "на Иртыше"},
        "room_quality": "курорт",
        "image_id": 507,
    },
    {
        "name": "Семей Абай Палас",
        "location": "Семей, проспект Абая",
        "services": {"Музей": "экскурсии", "Библиотека": "коллекция Абая"},
        "room_quality": "комфорт",
        "image_id": 508,
    },
    {
        "name": "Атырау Нефтяной Клуб",
        "location": "Атырау, проспект Азаттык",
        "services": {"SPA": "нефтяные ванны", "Бизнес-центр": "VIP залы"},
        "room_quality": "премиум",
        "image_id": 509,
    },
    {
        "name": "Актобе Западный Ветер",
        "location": "Актобе, проспект Абилкайыр хана",
        "services": {"Кафе": "казахская кухня", "Караоке": "казахские песни"},
        "room_quality": "комфорт",
        "image_id": 510,
    },
    {
        "name": "Костанай Тобыл Плаза",
        "location": "Костанай, улица Алтынсарина",
        "services": {"Торговый центр": "в здании", "Кинотеатр": "IMAX"},
        "room_quality": "бизнес",
        "image_id": 511,
    },
    {
        "name": "Петропавловск Северный",
        "location": "Петропавловск, проспект Конституции",
        "services": {"Трансфер": "к границе", "Экскурсии": "исторические"},
        "room_quality": "комфорт",
        "image_id": 512,
    },
    {
        "name": "Туркестан Яссауи Отель",
        "location": "Туркестан, мавзолей Ходжи Ахмеда Яссауи",
        "services": {"Экскурсии": "к мавзолею", "Мечеть": "на территории"},
        "room_quality": "премиум",
        "image_id": 513,
    },
    {
        "name": "Тараз Таразы Палас",
        "location": "Тараз, проспект Абая",
        "services": {"Бассейн": "крытый", "Теннис": "корты"},
        "room_quality": "делюкс",
        "image_id": 514,
    },
    {
        "name": "Кызылорда Сырдария",
        "location": "Кызылорда, набережная Сырдарьи",
        "services": {"Рыбалка": "на Сырдарье", "Лодки": "прокат"},
        "room_quality": "курорт",
        "image_id": 515,
    },
    {
        "name": "Уральск Жайык Плаза",
        "location": "Уральск, набережная Урала",
        "services": {"Ресторан": "рыбная кухня", "Прогулки": "по набережной"},
        "room_quality": "комфорт",
        "image_id": 516,
    },
    {
        "name": "Талдыкорган Жетысу",
        "location": "Талдыкорган, проспект Абая",
        "services": {"Горы": "экскурсии", "Мед": "местный"},
        "room_quality": "курорт",
        "image_id": 517,
    },
    {
        "name": "Экибастуз Энергетик",
        "location": "Экибастуз, проспект Независимости",
        "services": {"Бизнес-центр": "для переговоров", "Парковка": "бесплатная"},
        "room_quality": "бизнес",
        "image_id": 518,
    },
    {
        "name": "Рудный Соколовский",
        "location": "Рудный, проспект Мира",
        "services": {"Музей": "горнодобывающей промышленности", "Парк": "отдых"},
        "room_quality": "комфорт",
        "image_id": 519,
    },
    {
        "name": "Жезказган Медный",
        "location": "Жезказган, проспект Абая",
        "services": {"Экскурсии": "к рудникам", "Музей": "истории города"},
        "room_quality": "комфорт",
        "image_id": 520,
    },
    {
        "name": "Кокшетау Боровое",
        "location": "Кокшетау, курорт Боровое",
        "services": {"Озеро": "частный пляж", "Лес": "прогулки"},
        "room_quality": "курорт",
        "image_id": 521,
    },
    {
        "name": "Темиртау Металлург",
        "location": "Темиртау, проспект Металлургов",
        "services": {"Фитнес": "современный", "Бассейн": "олимпийский"},
        "room_quality": "бизнес",
        "image_id": 522,
    },
    {
        "name": "Актау Каспий Плаза",
        "location": "Актау, проспект Абая",
        "services": {"Пляж": "частный", "Дайвинг": "оборудование"},
        "room_quality": "премиум",
        "image_id": 523,
    },
    {
        "name": "Балхаш Озерный",
        "location": "Балхаш, набережная озера",
        "services": {"Пляж": "песчаный", "Рыбалка": "на озере"},
        "room_quality": "курорт",
        "image_id": 524,
    },
    {
        "name": "Сатпаев Академический",
        "location": "Сатпаев, проспект Академика Сатпаева",
        "services": {"Библиотека": "научная", "Конференции": "залы"},
        "room_quality": "бизнес",
        "image_id": 525,
    },
    {
        "name": "Кентау Шымкент Гейт",
        "location": "Кентау, шоссе Шымкентское",
        "services": {"Трансфер": "к Шымкенту", "Парковка": "большая"},
        "room_quality": "комфорт",
        "image_id": 526,
    },
    {
        "name": "Аральск Море",
        "location": "Аральск, бывшее побережье",
        "services": {"Музей": "истории Арала", "Экскурсии": "к высохшему морю"},
        "room_quality": "комфорт",
        "image_id": 527,
    },
    {
        "name": "Жанаозен Нефтяной",
        "location": "Жанаозен, проспект Нефтяников",
        "services": {"Бизнес-центр": "для нефтяников", "Ресторан": "европейская кухня"},
        "room_quality": "бизнес",
        "image_id": 528,
    },
    {
        "name": "Каскелен Алматы Гейт",
        "location": "Каскелен, трасса Алматы",
        "services": {"Трансфер": "к Алматы", "Парковка": "бесплатная"},
        "room_quality": "комфорт",
        "image_id": 529,
    },
    {
        "name": "Туркестан Паломнический",
        "location": "Туркестан, рядом с мавзолеем",
        "services": {"Мечеть": "на территории", "Гид": "религиозные экскурсии"},
        "room_quality": "премиум",
        "image_id": 530,
    },
]

# Данные для комнат (20 комнат)
KZ_ROOMS = [
    {
        "hotel_idx": 0,
        "name": "Люкс «Бәйтерек»",
        "descriptions": "Панорама на Есиль, дизайнерский юрточный декор.",
        "price_per_day": 88000,
        "services": {"Wi-Fi": "гигабитный", "Сауна": "инфракрасная"},
        "quality": "люкс",
        "image_id": 601,
    },
    {
        "hotel_idx": 0,
        "name": "Номер «Expo»",
        "descriptions": "Минимализм, умный дом и арт об Expo-2017.",
        "price_per_day": 64000,
        "services": {"VR-тур": "по павильонам EXPO", "Завтрак": "кулинария Акмола"},
        "quality": "бизнес",
        "image_id": 602,
    },
    {
        "hotel_idx": 1,
        "name": "Апартаменты «Алатау»",
        "descriptions": "Тёплые полы, камин BioLite и терраса с видом на горы.",
        "price_per_day": 72000,
        "services": {"Ски-камеры": "Чимбулак", "Трансфер": "Медеу"},
        "quality": "комфорт",
        "image_id": 603,
    },
    {
        "hotel_idx": 1,
        "name": "Студия «Верный»",
        "descriptions": "Современный дизайн с акцентами Верного и арт Устемира.",
        "price_per_day": 56000,
        "services": {"Бариста": "кофе на песке", "Велосипеды": "прокат"},
        "quality": "бизнес",
        "image_id": 604,
    },
    {
        "hotel_idx": 2,
        "name": "Сьют «Каспий»",
        "descriptions": "Панорамные окна на море, аква-сцена и лаунж зона.",
        "price_per_day": 68000,
        "services": {"Катер": "до острова Каратон", "Шеф": "каспийские морепродукты"},
        "quality": "курорт",
        "image_id": 605,
    },
    {
        "hotel_idx": 2,
        "name": "Вилла «Желмая»",
        "descriptions": "Приватная терраса, тандыр и аперитивы с видом на закат.",
        "price_per_day": 95000,
        "services": {"Йога": "на пляже", "SUP": "прокат досок"},
        "quality": "премиум",
        "image_id": 606,
    },
    {
        "hotel_idx": 3,
        "name": "Номер «Орда»",
        "descriptions": "Комнаты с резьбой Южного Казахстана и ароматным чаем.",
        "price_per_day": 43000,
        "services": {"Экскурсия": "к Арыстан баб", "Табылдылық": "ужин дегустация"},
        "quality": "комфорт",
        "image_id": 607,
    },
    {
        "hotel_idx": 3,
        "name": "Семейный «Сайрам»",
        "descriptions": "Две спальни, детская юрта и интерактив о Шымкенте.",
        "price_per_day": 51000,
        "services": {"Гид": "к ущелью Сайрам-Угам", "Транспорт": "кыз узату сервис"},
        "quality": "семейный",
        "image_id": 608,
    },
    {
        "hotel_idx": 4,
        "name": "Бизнес «Караганда»",
        "descriptions": "Рабочая зона, конференц-стол и вид на город.",
        "price_per_day": 55000,
        "services": {"Принтер": "в номере", "Кофе": "бесплатный"},
        "quality": "бизнес",
        "image_id": 609,
    },
    {
        "hotel_idx": 5,
        "name": "Стандарт «Иртыш»",
        "descriptions": "Уютный номер с видом на реку Иртыш.",
        "price_per_day": 38000,
        "services": {"Wi-Fi": "бесплатный", "Завтрак": "шведский стол"},
        "quality": "стандарт",
        "image_id": 610,
    },
    {
        "hotel_idx": 6,
        "name": "Горный «Алтай»",
        "descriptions": "Номер с балконом и видом на горы Алтая.",
        "price_per_day": 62000,
        "services": {"Терраса": "с мангалом", "Гид": "горные походы"},
        "quality": "комфорт",
        "image_id": 611,
    },
    {
        "hotel_idx": 7,
        "name": "Классик «Абай»",
        "descriptions": "Номер в стиле классической литературы Казахстана.",
        "price_per_day": 45000,
        "services": {"Библиотека": "книги Абая", "Чай": "казахский"},
        "quality": "комфорт",
        "image_id": 612,
    },
    {
        "hotel_idx": 8,
        "name": "Премиум «Нефть»",
        "descriptions": "Роскошный номер с нефтяной тематикой.",
        "price_per_day": 92000,
        "services": {"SPA": "нефтяные ванны", "Бар": "VIP"},
        "quality": "премиум",
        "image_id": 613,
    },
    {
        "hotel_idx": 9,
        "name": "Комфорт «Запад»",
        "descriptions": "Современный номер с элементами западного Казахстана.",
        "price_per_day": 48000,
        "services": {"Караоке": "в номере", "Кухня": "казахская"},
        "quality": "комфорт",
        "image_id": 614,
    },
    {
        "hotel_idx": 10,
        "name": "Бизнес «Тобыл»",
        "descriptions": "Номер для деловых поездок с рабочей зоной.",
        "price_per_day": 52000,
        "services": {"Факс": "в номере", "Конференц-зал": "доступ"},
        "quality": "бизнес",
        "image_id": 615,
    },
    {
        "hotel_idx": 11,
        "name": "Стандарт «Север»",
        "descriptions": "Уютный номер в северном стиле.",
        "price_per_day": 35000,
        "services": {"Wi-Fi": "бесплатный", "Завтрак": "континентальный"},
        "quality": "стандарт",
        "image_id": 616,
    },
    {
        "hotel_idx": 12,
        "name": "Люкс «Яссауи»",
        "descriptions": "Роскошный номер с видом на мавзолей.",
        "price_per_day": 85000,
        "services": {"Экскурсии": "к мавзолею", "Мечеть": "на территории"},
        "quality": "люкс",
        "image_id": 617,
    },
    {
        "hotel_idx": 13,
        "name": "Делюкс «Таразы»",
        "descriptions": "Просторный номер с современным дизайном.",
        "price_per_day": 68000,
        "services": {"Бассейн": "доступ", "Теннис": "корты"},
        "quality": "делюкс",
        "image_id": 618,
    },
    {
        "hotel_idx": 14,
        "name": "Курорт «Сырдария»",
        "descriptions": "Номер с видом на реку Сырдарью.",
        "price_per_day": 58000,
        "services": {"Рыбалка": "оборудование", "Лодки": "прокат"},
        "quality": "курорт",
        "image_id": 619,
    },
    {
        "hotel_idx": 15,
        "name": "Комфорт «Жайык»",
        "descriptions": "Номер с видом на реку Урал.",
        "price_per_day": 42000,
        "services": {"Ресторан": "рыбная кухня", "Прогулки": "набережная"},
        "quality": "комфорт",
        "image_id": 620,
    },
]


async def create_users(session) -> List[User]:
    """Создает пользователей в базе данных."""
    # Проверяем, существуют ли уже пользователи
    admin_user = await session.scalar(
        select(User).where(User.email == "admin@example.com")
    )
    regular_user = await session.scalar(
        select(User).where(User.email == "user@example.com")
    )

    users_to_create = []

    if not admin_user:
        admin_user = User(
            email="admin@example.com",
            hash_password=hash_password("admin123"),
            first_name="Админ",
            last_name="Админыч",
            role=RolesEnum.ADMIN,
        )
        users_to_create.append(admin_user)

    if not regular_user:
        regular_user = User(
            email="user@example.com",
            hash_password=hash_password("user12345"),
            first_name="Иван",
            last_name="Петров",
            role=RolesEnum.USER,
        )
        users_to_create.append(regular_user)

    if users_to_create:
        session.add_all(users_to_create)
        await session.flush()
        print(f"Создано пользователей: {len(users_to_create)}")
    else:
        print("Пользователи уже существуют")
        admin_user = await session.scalar(
            select(User).where(User.email == "admin@example.com")
        )
        regular_user = await session.scalar(
            select(User).where(User.email == "user@example.com")
        )
        users_to_create = [admin_user, regular_user]

    return users_to_create


async def create_hotels(session) -> List[Hotel]:
    """Создает отели в базе данных."""
    # Проверяем количество существующих отелей
    existing_count = await session.scalar(select(func.count(Hotel.id)))

    if existing_count >= 30:
        print(f"Отелей уже достаточно: {existing_count}")
        result = await session.scalars(select(Hotel))
        return list(result)

    # Создаем недостающие отели
    hotels_to_create = []
    for hotel_data in KZ_HOTELS:
        # Проверяем, существует ли отель с таким именем
        existing = await session.scalar(
            select(Hotel).where(Hotel.name == hotel_data["name"])
        )
        if not existing:
            hotel = Hotel(**hotel_data)
            hotels_to_create.append(hotel)

    if hotels_to_create:
        session.add_all(hotels_to_create)
        await session.flush()
        print(f"Создано отелей: {len(hotels_to_create)}")

    # Получаем все отели
    result = await session.scalars(select(Hotel))
    all_hotels = list(result)

    return all_hotels


async def create_rooms(session, hotels: List[Hotel]) -> List[Room]:
    """Создает комнаты в базе данных."""
    # Проверяем количество существующих комнат
    existing_count = await session.scalar(select(func.count(Room.id)))

    if existing_count >= 20:
        print(f"Комнат уже достаточно: {existing_count}")
        result = await session.scalars(select(Room))
        return list(result)

    # Создаем недостающие комнаты
    rooms_to_create = []
    for room_data in KZ_ROOMS:
        # Проверяем, существует ли комната с таким именем
        existing = await session.scalar(
            select(Room).where(Room.name == room_data["name"])
        )
        if not existing:
            hotel_idx = room_data["hotel_idx"]
            if hotel_idx < len(hotels):
                hotel = hotels[hotel_idx]
                room = Room(
                    hotel_id=hotel.id,
                    name=room_data["name"],
                    descriptions=room_data["descriptions"],
                    price_per_day=room_data["price_per_day"],
                    services=room_data["services"],
                    quality=room_data["quality"],
                    image_id=room_data["image_id"],
                )
                rooms_to_create.append(room)

    if rooms_to_create:
        session.add_all(rooms_to_create)
        await session.flush()
        print(f"Создано комнат: {len(rooms_to_create)}")

    # Получаем все комнаты
    result = await session.scalars(select(Room))
    all_rooms = list(result)

    return all_rooms


async def create_bookings(session, users: List[User], rooms: List[Room]) -> None:
    """Создает бронирования в базе данных."""
    if not rooms:
        print("Нет комнат для создания бронирований")
        return

    if not users:
        print("Нет пользователей для создания бронирований")
        return

    # Проверяем существующие бронирования
    existing_count = await session.scalar(select(func.count(Booking.id)))

    if existing_count >= 10:
        print(f"Бронирований уже достаточно: {existing_count}")
        return

    # Создаем бронирования
    random.seed(42)  # Для воспроизводимости
    bookings_to_create = []
    start_date = date.today()

    # Создаем 10-15 бронирований
    for i in range(15):
        user = random.choice(users)
        room = random.choice(rooms)

        # Случайные даты в будущем
        offset_days = random.randint(1, 60)
        stay_length = random.randint(1, 7)
        arrival = start_date + timedelta(days=offset_days)
        departure = arrival + timedelta(days=stay_length)

        total_cost = room.price_per_day * stay_length

        # Случайный статус
        status = random.choice(
            [BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.CANCELLED]
        )

        booking = Booking(
            date_from=arrival,
            date_to=departure,
            price_per_day=room.price_per_day,
            totals_day=stay_length,
            total_cost=total_cost,
            user_id=user.id,
            status=status,
        )
        booking.rooms.append(room)
        bookings_to_create.append(booking)

    if bookings_to_create:
        session.add_all(bookings_to_create)
        await session.flush()
        print(f"Создано бронирований: {len(bookings_to_create)}")
    else:
        print("Бронирования не созданы")


async def main() -> None:
    """Основная функция для наполнения базы данных."""
    print("Инициализация моделей...")
    await init_models()

    print("Подключение к базе данных...")
    async with AsyncSessionFactory() as session:
        print("\n=== Создание пользователей ===")
        users = await create_users(session)

        print("\n=== Создание отелей ===")
        hotels = await create_hotels(session)

        print("\n=== Создание комнат ===")
        rooms = await create_rooms(session, hotels)

        print("\n=== Создание бронирований ===")
        await create_bookings(session, users, rooms)

        print("\n=== Сохранение изменений ===")
        await session.commit()
        print("Все данные успешно сохранены в базу данных!")

        # Выводим статистику
        print("\n=== Статистика ===")
        users_count = await session.scalar(select(func.count(User.id)))
        hotels_count = await session.scalar(select(func.count(Hotel.id)))
        rooms_count = await session.scalar(select(func.count(Room.id)))
        bookings_count = await session.scalar(select(func.count(Booking.id)))

        print(f"Пользователей: {users_count}")
        print(f"Отелей: {hotels_count}")
        print(f"Комнат: {rooms_count}")
        print(f"Бронирований: {bookings_count}")


if __name__ == "__main__":
    asyncio.run(main())

"""
docker compose run --rm db_seeder
"""
