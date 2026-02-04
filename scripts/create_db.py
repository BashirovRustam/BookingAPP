"""Скрипт для наполнения базы данных Postgres в Docker контейнере."""

import asyncio
import random
from datetime import date, timedelta
from typing import List, Dict

from sqlalchemy import func, select

from app.Booking.models import Booking, BookingStatus
from app.BookingRooms.models import BookingRooms
from app.Hotel.models import Hotel
from app.Room.models import Room
from app.User.models import User, RolesEnum
from app.User.User_auth.security import hash_password
from app.db.base import AsyncSessionFactory, init_models

# Базовые данные для генерации отелей
KAZAKHSTAN_CITIES = [
    "Астана", "Алматы", "Шымкент", "Караганда", "Актау", "Атырау", 
    "Актобе", "Павлодар", "Усть-Каменогорск", "Семей", "Костанай",
    "Петропавловск", "Туркестан", "Тараз", "Кызылорда", "Уральск",
    "Талдыкорган", "Экибастуз", "Рудный", "Жезказган", "Кокшетау",
    "Темиртау", "Балхаш", "Сатпаев", "Кентау", "Аральск", "Жанаозен",
    "Каскелен", "Капшагай", "Риддер", "Лисаковск", "Сарань", "Степногорск",
    "Шахтинск", "Байконур", "Аксу", "Аксуск", "Жаркент", "Талгар",
    "Есик", "Шу", "Сарыагаш", "Аралык", "Кульсары", "Жетысай"
]

HOTEL_NAMES_PARTS = [
    "Премиум", "Гранд", "Плаза", "Отель", "Резорт", "Палас", "Роял", 
    "Люксовый", "Комфорт", "Бизнес", "Классик", "Модерн", "Центральный",
    "Национальный", "Золотой", "Серебряный", "Алмазный", "Изумрудный",
    "Солнечный", "Горный", "Озерный", "Речной", "Степной", "Небесный"
]

HOTEL_THEMES = [
    "Бәйтерек", "Абай", "Яссауи", "Алатау", "Каспий", "Иртыш", "Сырдария",
    "Жайык", "Балхаш", "Алтай", "Тянь-Шань", "Сарыарка", "Урал", "Тобол",
    "Есиль", "Нура", "Шу", "Лепсы", "Кокшетау", "Боровое", "Байконур"
]

SERVICES_POOL = {
    "SPA": ["хаммам и бассейн", "сауна и джакузи", "массаж и релакс", "термальные ванны", "ароматерапия"],
    "Трансфер": ["аэропорт", "ж/д вокзал", "автовокзал", "центр города", "курортная зона"],
    "Ресторан": ["европейская кухня", "казахская кухня", "азиатская кухня", "французская кухня", "итальянская кухня"],
    "Фитнес": ["современное оборудование", "тренажерный зал", "йога студия", "кардио зона", "силовые тренировки"],
    "Бассейн": ["крытый", "открытый", "олимпийский", "детский", "с подогревом"],
    "Конференц-зал": ["на 50 человек", "на 100 человек", "на 200 человек", "VIP зал", "переговорная"],
    "Парковка": ["бесплатная", "подземная", "охраняемая", "VIP парковка", "гостевая"],
    "Wi-Fi": ["бесплатный", "гигабитный", "высокоскоростной", "безопасный", "VIP доступ"],
    "Экскурсии": ["исторические", "природные", "городские", "культурные", "гастрономические"],
    "Развлечения": ["караоке", "бильярд", "боулинг", "кинотеатр", "игровая зона"],
    "Бизнес": ["бизнес-центр", "офисные услуги", "переводчик", "секретарь", "VIP зал"],
    "Спорт": ["теннисные корты", "футбольное поле", "баскетбольная площадка", "волейбольная площадка", "беговая дорожка"],
    "Красота": ["парикмахерская", "салон красоты", "маникюр", "педикюр", "косметология"],
    "Дети": ["детская комната", "игровая площадка", "аниматор", "детский клуб", "няня"],
    "Питание": ["завтрак", "обед", "ужин", "шведский стол", "room service"],
    "Комфорт": ["кондиционер", "минибар", "сейф", "халаты", "обувь"],
    "Технологии": ["умный дом", "смарт ТВ", "Apple TV", "Bluetooth колонка", "игровая консоль"],
    "Пляж": ["частный", "общественный", "песчаный", "галечный", "дикий"],
    "Горы": ["экскурсии", "подъемник", "горнолыжка", "пешие походы", "альпинизм"],
    "Вода": ["рыбалка", "катание на лодках", "яхтинг", "дайвинг", "серфинг"],
    "Культура": ["музей", "галерея", "театр", "концертный зал", "библиотека"],
    "Шоппинг": ["торговый центр", "бутики", "сувенирный магазин", "антикварный", "дизайнерский"]
}

ROOM_QUALITIES = ["стандарт", "комфорт", "делюкс", "люкс", "премиум", "бизнес", "курорт", "семейный"]

ROOM_DESCRIPTIONS = [
    "Уютный номер с панорамными окнами и современным дизайном",
    "Просторный номер с рабочей зоной и высокоскоростным интернетом",
    "Элегантный номер с дизайнерской мебелью и атмосферным освещением",
    "Комфортный номер с удобной кроватью и качественным бельем",
    "Стильный номер с минималистичным интерьером и современной техникой",
    "Роскошный номер с панорамным видом и премиум отделкой",
    "Функциональный номер с кухонной зоной и обеденным столом",
    "Семейный номер с дополнительными спальными местами и игровой зоной",
    "Романтический номер с джакузи и балконом с цветами",
    "Бизнес номер с конференц-столом и офисным оборудованием",
    "Экологичный номер с натуральными материалами и зелеными растениями",
    "Технологичный номер с умным домом и голосовым управлением",
    "Традиционный номер с национальными элементами декора",
    "Современный номер с открытой планировкой и террасой",
    "Классический номер с деревянной мебелью и антикварными деталями",
    "Минималистичный номер с функциональной мебелью и скрытым хранением",
    "Арт-номер с картинами и скульптурами местных художников",
    "Лофт номер с высокими потолками и индустриальным дизайном",
    "Скандинавский номер с светлыми тонами и уютной атмосферой",
    "Японский номер с минимализмом и традиционными элементами"
]

ROOM_SERVICES_POOL = {
    "Wi-Fi": ["бесплатный", "гигабитный", "высокоскоростной", "безопасный", "VIP доступ"],
    "Кондиционер": ["инверторный", "умный", "тихий", "мощный", "энергоэффективный"],
    "ТВ": ["смарт ТВ", "4K телевизор", "кабельное ТВ", "спутниковое ТВ", "3D телевизор"],
    "Минибар": ["бесплатный", "пополняемый", "VIP наполнение", "местные напитки", "импортные напитки"],
    "Сейф": ["электронный", "отдельный", "большой", "ноутбук сейф", "биометрический"],
    "Балкон": ["с видом на город", "с видом на горы", "с мебелью", "терраса", "летняя веранда"],
    "Ванная": ["джакузи", "душ кабина", "гидромассаж", "фен", "банные халаты"],
    "Кухня": ["кухонная зона", "кухня-студия", "кофемашина", "плита", "холодильник"],
    "Рабочая зона": ["письменный стол", "офисное кресло", "лампа", "розетки", "USB порты"],
    "Развлечения": ["игровая консоль", "Apple TV", "Bluetooth колонка", "VR очки", "проектор"],
    "Комфорт": ["ортопедический матрас", "пуховые одеяла", "гипоаллергенные подушки", "пижамы", "тапочки"],
    "Технологии": ["умный дом", "голосовое управление", "автоматизация", "сценарии освещения", "климат-контроль"],
    "Питание": ["room service", "кофемашина", "чайник", "холодильник", "микроволновка"],
    "Спорт": ["тренажер", "велотренажер", "йога коврик", "гантели", "экспандер"],
    "Красота": ["зеркало с подсветкой", "фен", "утюжок", "набор косметики", "зеркало для макияжа"],
    "Дети": ["детская кроватка", "стульчик для кормления", "игрушки", "детские книги", "мультики"],
    "Экология": ["очиститель воздуха", "фильтрованная вода", "органическая косметика", "натуральные материалы", "энергосбережение"],
    "Безопасность": ["противопожарная система", "датчик дыма", "тревожная кнопка", "видеонаблюдение", "электронный замок"],
    "Люксовое": ["халаты", "тапочки", "дополнительные услуги", "VIP обслуживание", "персональный ассистент"],
    "Бизнес": ["принтер", "сканер", "факс", "конференц-звонок", "многозонный розеточный блок"],
    "Отдых": ["массажное кресло", "гамак", "подвесное кресло", "солярий", "медитационная зона"]
}

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

def generate_hotels(count: int = 2000) -> List[Dict]:
    """Генерирует указанное количество отелей с разнообразными услугами."""
    hotels = []
    
    for i in range(count):
        city = random.choice(KAZAKHSTAN_CITIES)
        name_part1 = random.choice(HOTEL_NAMES_PARTS)
        name_part2 = random.choice(HOTEL_THEMES)
        
        # Генерируем уникальное имя
        hotel_name = f"{name_part1} {name_part2}"
        
        # Генерируем локацию
        street_options = ["проспект", "улица", "набережная", "бульвар", "площадь", "мкр", "микрорайон"]
        street_name = random.choice(["Абая", "Назарбаева", "Достык", "Республики", "Бауыржана", "Сатпаева", "Пушкина", "Ленина", "Мира", "Конституции"])
        street_type = random.choice(street_options)
        location = f"{city}, {street_type} {street_name}"
        
        # Генерируем услуги (2-5 услуг на отель)
        num_services = random.randint(2, 5)
        available_services = list(SERVICES_POOL.keys())
        selected_services = random.sample(available_services, min(num_services, len(available_services)))
        
        services = {}
        for service in selected_services:
            service_options = SERVICES_POOL[service]
            services[service] = random.choice(service_options)
        
        # Генерируем качество
        room_quality = random.choice(ROOM_QUALITIES)
        
        # Генерируем image_id
        image_id = 500 + i % 1000  # Уникальные ID от 500 до 1499
        
        hotels.append({
            "name": hotel_name,
            "location": location,
            "services": services,
            "room_quality": room_quality,
            "image_id": image_id,
        })
    
    return hotels

def generate_rooms(count: int = 1000, hotel_count: int = 2000) -> List[Dict]:
    """Генерирует указанное количество комнат с разнообразными описаниями и услугами."""
    rooms = []
    
    room_name_parts = ["Люкс", "Сьют", "Апартаменты", "Студия", "Номер", "Вилла", "Коттедж", "Бунгало", "Пентхаус", "Дуплекс"]
    room_themes = ["Бәйтерек", "Абай", "Яссауи", "Алатау", "Каспий", "Иртыш", "Сырдария", "Жайык", "Алтай", "Тянь-Шань"]
    
    for i in range(count):
        hotel_idx = random.randint(0, hotel_count - 1)
        name_part1 = random.choice(room_name_parts)
        name_part2 = random.choice(room_themes)
        
        # Генерируем уникальное имя комнаты
        room_name = f"{name_part1} «{name_part2}»"
        
        # Генерируем описание
        description = random.choice(ROOM_DESCRIPTIONS)
        
        # Генерируем цену (от 15000 до 150000 тг)
        base_price = random.randint(15000, 150000)
        
        # Генерируем услуги (2-4 услуги на комнату)
        num_services = random.randint(2, 4)
        available_services = list(ROOM_SERVICES_POOL.keys())
        selected_services = random.sample(available_services, min(num_services, len(available_services)))
        
        services = {}
        for service in selected_services:
            service_options = ROOM_SERVICES_POOL[service]
            services[service] = random.choice(service_options)
        
        # Генерируем качество
        quality = random.choice(ROOM_QUALITIES)
        
        # Генерируем image_id
        image_id = 600 + i % 1000  # Уникальные ID от 600 до 1599
        
        rooms.append({
            "hotel_idx": hotel_idx,
            "name": room_name,
            "descriptions": description,
            "price_per_day": base_price,
            "services": services,
            "quality": quality,
            "image_id": image_id,
        })
    
    return rooms

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

    if existing_count >= 2000:
        print(f"Отелей уже достаточно: {existing_count}")
        result = await session.scalars(select(Hotel))
        return list(result)

    # Создаем базовые отели если их нет
    hotels_to_create = []
    for hotel_data in KZ_HOTELS:
        # Проверяем, существует ли отель с таким именем
        existing = await session.scalar(
            select(Hotel).where(Hotel.name == hotel_data["name"])
        )
        if not existing:
            hotel = Hotel(**hotel_data)
            hotels_to_create.append(hotel)

    # Генерируем дополнительные отели если нужно
    target_count = 2000
    if existing_count + len(hotels_to_create) < target_count:
        additional_needed = target_count - existing_count - len(hotels_to_create)
        generated_hotels = generate_hotels(additional_needed)
        
        for hotel_data in generated_hotels:
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

    if existing_count >= 1000:
        print(f"Комнат уже достаточно: {existing_count}")
        result = await session.scalars(select(Room))
        return list(result)

    # Создаем базовые комнаты если их нет
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

    # Генерируем дополнительные комнаты если нужно
    target_count = 1000
    if existing_count + len(rooms_to_create) < target_count:
        additional_needed = target_count - existing_count - len(rooms_to_create)
        hotel_count = len(hotels) if hotels else 2000
        generated_rooms = generate_rooms(additional_needed, hotel_count)
        
        for room_data in generated_rooms:
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
