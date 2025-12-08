# Руководство по тестированию с pytest

Это руководство объясняет, как тестировать ваш проект BookingAPP с помощью pytest.

## 📋 Содержание

1. [Установка зависимостей](#установка-зависимостей)
                               2. [Структура тестов](#структура-тестов)
3. [Запуск тестов](#запуск-тестов)
4. [Основные концепции](#основные-концепции)
5. [Примеры тестов](#примеры-тестов)
6. [Лучшие практики](#лучшие-практики)

---

## Установка зависимостей

Установите зависимости для тестирования:

```bash
pip install -r requirements.txt
```

Или только тестовые зависимости:

```bash
pip install pytest pytest-asyncio pytest-cov
```

---

## Структура тестов

```
BookingAPP/
├── tests/
│   ├── __init__.py          # Пустой файл для создания пакета
│   ├── conftest.py          # Фикстуры (fixtures) для всех тестов
│   ├── test_booking_crud.py # Тесты для CRUD операций с бронированиями
│   └── README.md            # Это руководство
├── pytest.ini               # Конфигурация pytest
└── requirements.txt         # Зависимости проекта
```

### conftest.py

Файл `conftest.py` содержит **фикстуры** (fixtures) - переиспользуемые объекты для тестов:

- `test_engine` - тестовый движок базы данных
- `test_session` - тестовая сессия SQLAlchemy
- `sample_hotel` - тестовый отель
 - `sample_room` - тестовая комната
                                                                                                                                 - `sample_user` - тестовый пользователь
                                                                                                                                                            - `sample_booking` - тестовое бронирование

Фикстуры автоматически доступны во всех тестах без импорта.

                                                   ---

## Запуск тестов

### Запуск всех тестов

```bash
pytest
```

### Запуск конкретного файла

```bash
pytest tests/test_booking_crud.py
```

### Запуск конкретного теста

```bash
pytest tests/test_booking_crud.py::test_create_booking_success
```

### Запуск с подробным выводом

```bash
pytest -v
```

### Запуск с покрытием кода

```bash
pytest --cov=app --cov-report=html
```

После этого откройте `htmlcov/index.html` в браузере.

### Запуск только быстрых тестов

```bash
pytest -m "not slow"
```

---

## Основные концепции

### 1. Асинхронные тесты

Поскольку ваш проект использует асинхронные функции, тесты тоже должны быть асинхронными:

```python
   @pytest.mark.asyncio
async def test_my_function(test_session):
    result = await my_async_function(test_session)
    assert result is not None
```

Декоратор `@pytest.mark.asyncio` указывает pytest, что тест асинхронный.

### 2. Фикстуры (Fixtures)

Фикстуры - это функции, которые подготавливают данные для тестов:

```python
@pytest.fixture
async def sample_user(test_session):
    user = User(email="test@example.com", ...)
    test_session.add(user)
    await test_session.commit()
    return user
```

Использование в тесте:

```python
async def test_something(test_session, sample_user):
    # sample_user уже создан и доступен
    assert sample_user.email == "test@example.com"
```

### 3. Scope фикстур

- `scope="function"` (по умолчанию) - создаётся для каждого теста
- `scope="class"` - создаётся один раз для класса тестов
- `scope="module"` - создаётся один раз для модуля
- `scope="session"` - создаётся один раз для всей сессии тестов

### 4. Arrange-Act-Assert (AAA)

Структура теста:

```python
async def test_example(test_session, sample_user):
    # Arrange (Подготовка) - настройка данных
    date_from = date.today() + timedelta(days=10)

    # Act (Действие) - выполнение тестируемой функции
    result = await crud.create_booking(test_session, ...)

    # Assert (Проверка) - проверка результата
    assert result is not None
    assert result.date_from == date_from
```

---

## Примеры тестов

### Пример 1: Тест создания

```python
@pytest.mark.asyncio
async def test_create_booking_success(test_session, sample_user, sample_room):
    # Подготовка
    booking_data = BookingCreate(
        date_from=date.today() + timedelta(days=10),
        date_to=date.today() + timedelta(days=15),
        price_per_day=Decimal("15000.00"),
        room_id=sample_room.id,
    )

    # Выполнение
    created_booking = await crud.create_booking(
        test_session,
        booking_data,
        sample_user.id,
    )

    # Проверка
    assert created_booking is not None
    assert created_booking.id is not None
    assert created_booking.totals_day == 5
```

### Пример 2: Тест получения

```python
@pytest.mark.asyncio
async def test_get_booking_by_id_success(test_session, sample_booking):
    booking = await crud.get_booking_by_id(test_session, sample_booking.id)

    assert booking is not None
    assert booking.id == sample_booking.id
```

### Пример 3: Тест обновления

```python
@pytest.mark.asyncio
async def test_update_booking_success(test_session, sample_booking):
    update_data = BookingUpdate(date_to=date.today() + timedelta(days=20))

    updated_booking = await crud.update_booking(
        test_session,
        sample_booking.id,
        update_data,
    )

    assert updated_booking is not None
    assert updated_booking.date_to == update_data.date_to
```

### Пример 4: Тест удаления

```python
@pytest.mark.asyncio
async def test_delete_booking_success(test_session, sample_booking):
    result = await crud.delete_booking(test_session, sample_booking.id)

    assert result is True

    # Проверяем, что бронирование удалено
    deleted_booking = await crud.get_booking_by_id(
        test_session,
        sample_booking.id
    )
    assert deleted_booking is None
```

### Пример 5: Тест граничного случая

```python
@pytest.mark.asyncio
async def test_get_booking_by_id_not_found(test_session):
    booking = await crud.get_booking_by_id(test_session, 99999)
    assert booking is None
```

---

## Лучшие практики

### ✅ DO (Делайте так)

1. **Используйте понятные имена тестов**
```python
# ✅ Хорошо
async def test_create_booking_success(...)
    async def test_get_booking_by_id_not_found(...)

# ❌ Плохо
async def test1(...)
    async def test_booking(...)
    ```

2. **Один тест - одна проверка**
```python
# ✅ Хорошо - каждый тест проверяет одну вещь
async def test_booking_has_correct_date_from(...)
    async def test_booking_has_correct_total_cost(...)
    ```

3. **Используйте фикстуры для переиспользования**
```python
# ✅ Хорошо - используем фикстуру
async def test_something(test_session, sample_user):
    ...
```

4. **Тестируйте граничные случаи**
- Несуществующие ID
- Пустые данные
- Некорректные значения
- Конфликты данных

5. **Используйте AAA паттерн** (Arrange-Act-Assert)

### ❌ DON'T (Не делайте так)

1. **Не используйте реальную базу данных**
- Используйте SQLite в памяти (`:memory:`)
- Или используйте тестовую БД, которая очищается после тестов

2. **Не делайте тесты зависимыми друг от друга**
- Каждый тест должен быть независимым
- Тесты должны запускаться в любом порядке

3. **Не тестируйте внешние зависимости напрямую**
- Используйте моки (mocks) для внешних API
- Используйте фикстуры для данных

4. **Не игнорируйте ошибки**
```python
# ❌ Плохо
try:
    result = await function()
except:
    pass

# ✅ Хорошо
with pytest.raises(ValueError):
    await function()
```

---

## Полезные команды pytest

```bash
# Показать все доступные тесты
pytest --collect-only

# Запустить тесты и остановиться на первой ошибке
pytest -x

# Запустить тесты в параллель (требует pytest-xdist)
pytest -n auto

# Показать print() в тестах
pytest -s

# Запустить только тесты, содержащие "create" в имени
pytest -k create

# Запустить тесты с маркером "slow"
pytest -m slow

# Пропустить тесты с маркером "slow"
pytest -m "not slow"
```

---

## Отладка тестов

### Использование print()

```python
async def test_debug(test_session, sample_user):
    print(f"User ID: {sample_user.id}")  # Будет видно с флагом -s
    assert sample_user.id is not None
```

### Использование отладчика

```python
async def test_debug(test_session, sample_user):
    import pdb; pdb.set_trace()  # Точка останова
    assert sample_user.id is not None
```

### Использование pytest.raises для проверки исключений

```python
async def test_validation_error(test_session):
    with pytest.raises(ValueError, match="Нельзя бронировать прошедшие даты"):
        booking_data = BookingCreate(
            date_from=date.today() - timedelta(days=1),  # Прошедшая дата
            date_to=date.today() + timedelta(days=5),
            price_per_day=Decimal("15000.00"),
            room_id=1,
        )
```

---

## Дополнительные ресурсы

- [Официальная документация pytest](https://docs.pytest.org/)
- [pytest-asyncio документация](https://pytest-asyncio.readthedocs.io/)
- [SQLAlchemy тестирование](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)

                                    ---

## Вопросы и проблемы

Если у вас возникли проблемы:

1. Убедитесь, что все зависимости установлены
2. Проверьте, что pytest.ini настроен правильно
3. Убедитесь, что тесты используют `@pytest.mark.asyncio`
4. Проверьте, что фикстуры правильно определены в conftest.py