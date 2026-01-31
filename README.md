# 🏨 **Booking Service** — Pet Project


Современный асинхронный backend-сервис бронирования отелей
на **FastAPI** с production-подходами


---

## 🛠️ Стек технологий:

<p align="center">

[![Python](https://img.shields.io/badge/Python-464646?style=flat-square\&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-464646?style=flat-square\&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Anyio](https://img.shields.io/badge/Anyio-464646?style=flat-square\&logo=anyio)](https://anyio.readthedocs.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-464646?style=flat-square\&logo=postgresql)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-464646?style=flat-square\&logo=sqlalchemy)](https://www.sqlalchemy.org/)
[![Docker](https://img.shields.io/badge/Docker-464646?style=flat-square\&logo=docker)](https://www.docker.com/)
[![Redis](https://img.shields.io/badge/Redis-464646?style=flat-square\&logo=redis)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-464646?style=flat-square\&logo=celery)](https://docs.celeryq.dev/)

</p>

---

## 📌 О проекте

**Booking Service** — это асинхронный backend-сервис для бронирования гостиничных номеров.
Проект реализован как **pet-project**, но с ориентацией на **production-архитектуру**, приближенную к реальным коммерческим системам.

### 🧩 Архитектурный подход

Проект построен по **гибридной архитектуре (Monolith + Microservices)**:

* 🧱 **Монолит сервиса бронирования** — отвечает за:

  * управление отелями, комнатами и типами номеров
  * бизнес-логику бронирований и валидации
  * пользователей, аутентификацию и доступы

* 🔗 **Выделенные микросервисы**:

  * ✉️ **Notification Service** — email-уведомления, подтверждения бронирования, отправка чеков
  * 💳 **Payment Service** — обработка оплат и приём webhook-событий (тестовый PayPal)

### 🔌 Взаимодействие сервисов

* Все сервисы взаимодействуют **по HTTP (REST)**
* Используется асинхронный I/O
* Webhook-события обрабатываются неблокирующим образом
* Критичная логика вынесена в фоновые задачи

### 🔹 Ключевые возможности

* 🔹 Поиск отелей по локации и датам
* 🔹 Бронирование номеров
* 🔹 Асинхронная обработка событий и фоновых задач
* 🔹 Интеграция с платёжным провайдером через webhooks
* 🔹 Кеширование, мониторинг и логирование
* 🔹 Полная Docker-инфраструктура

Проект демонстрирует уверенное владение **FastAPI**, **async Python**, **HTTP-взаимодействием между сервисами**, **очередями задач** и **чистой backend-архитектурой**.

---

## 🚀 Возможности

### 👤 Аутентификация и пользователи

* 🔐 Кастомная регистрация пользователей
* 🍪 Аутентификация через **JWT + Cookies**
* 🛡️ Разграничение прав доступа
* 👁️ Read-only доступ для неаутентифицированных пользователей
* 🙋 Получение информации о текущем пользователе

---

### 🏨 Отели и номера

* 📋 Получение списка всех отелей
* 🔍 Поиск отелей по локации и датам
* 🏢 Детальная информация по отелю
* 🚪 Список доступных номеров на выбранные даты
* 🛏️ Типы комнат и информация по ним

---

### 📅 Бронирование

* ➕ Создание бронирования
* 📖 Просмотр всех своих бронирований
* ❌ Отмена бронирования
* ⏳ Валидация дат (нельзя бронировать прошедшие даты)

---

### ✉️ Асинхронные задачи и события

- 📧 **Email-уведомления пользователям**  
  — подтверждение бронирования  
  — уведомления о смене статуса операций  
  Реализовано через **Celery + aiosmtplib**  
  (локально используется **MailHog** для тестирования)

- 🔔 **Асинхронная обработка внешних webhook-событий**  
  — приём и валидация webhook-запросов от платёжного провайдера (тестовый PayPal)  
  — неблокирующая обработка событий без влияния на основной API  
  — событийная модель взаимодействия между сервисами

- 🧾 **Отправка чеков и подтверждений оплаты**  
  — email с чеком отправляется **только после успешного подтверждённого webhook-события**  
  — бизнес-логика вынесена в фоновые задачи Celery

- ⚡ **Redis** используется как:\n  - broker очередей задач Celery  \n  - кеш для ускорения повторяющихся запросов  \n  - временное хранилище для снижения нагрузки на БД

- 🧠 **Event-driven подход**  
  — бизнес-события (booking created, payment confirmed) инициируют цепочки фоновых задач  
  — повышает отказоустойчивость и масштабируемость системы


---

## 🧱 Архитектура

* Асинхронный backend (FastAPI + AnyIO)
* SQLAlchemy 2.0 (async ORM)
* Слоистая архитектура:

  * **API (routers)**
  * **Services (business logic)**
  * **Repositories (DB access)**
* Версионирование API: `/api/v1`
* Подготовленные сиды для базы данных

---

## 📚 API Документация

После запуска проекта документация доступна по адресу:

👉 **[http://localhost:8000/v1/docs/](http://localhost:8000/v1/docs/)**

---

## 🧰 Используемые технологии

### 🔹 Backend

* Python 3.9+
* FastAPI
* Starlette
* Pydantic v2
* AnyIO / AsyncIO

### 🔹 Database

* PostgreSQL
* SQLAlchemy 2.0 (async)
* Alembic
* asyncpg / psycopg

### 🔹 Background & Cache

* Celery 5.4
* Redis 5
* Flower

### 🔹 Security

* JWT (python-jose)
* Cookies
* Argon2 / bcrypt
* Passlib

### 🔹 DevOps & Observability

* Docker & Docker Compose
* Uvicorn + UVLoop


### 🔹 Testing & Utils

* pytest + pytest-asyncio
* HTTPX
* Pillow
* fastapi-cache2
* Black

---

## ▶️ Локальный запуск

### 🔧 Требования

* Docker
* Docker Compose
* Git

---

### 📥 Клонирование репозитория

```bash
git clone https://github.com/yourusername/booking-service.git
cd booking-service
```

#### 2️⃣ Настройка виртуального окружения

Создайте и активируйте виртуальное окружение для изоляции зависимостей проекта:

**🪟 Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**🪟 Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**🐧 Linux / 🍎 macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 4️⃣ Запуск Docker-инфраструктуры

Соберите и запустите все сервисы (PostgreSQL, Redis, Celery, API):

```bash
docker-compose up --build
```

> ⏳ **Подождите**, пока все контейнеры успешно запустятся. В логах вы увидите сообщения о готовности сервисов.

#### 5️⃣ Наполнение базы данных

В **отдельном терминале** выполните команду для инициализации БД тестовыми данными:

```bash
docker compose run --rm db_seeder
```

Эта команда запустит одноразовый контейнер, который:
- Создаст начальные записи (отели, номера, пользователей)
- Автоматически завершит работу после выполнения


👥 Тестовые пользователи после seed:
<table>
<thead>
  <tr>
    <th align="center">Роль</th>
    <th>Email</th>
    <th>Пароль</th>
    <th>Описание</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td align="center">🔑 <strong>Admin</strong></td>
    <td><code>admin@example.com</code></td>
    <td><code>admin123</code></td>
    <td>Полный доступ ко всем операциям</td>
  </tr>
  <tr>
    <td align="center">👤 <strong>User</strong></td>
    <td><code>user@example.com</code></td>
    <td><code>user12345</code></td>
    <td>Стандартный пользователь</td>
  </tr>
</tbody>
</table>

💡 Tip: Используйте эти учетные данные для тестирования API через Swagger UI

#### ✅ Готово!

Сервис доступен по адресу:
- 🌐 **API:** [http://localhost:8000](http://localhost:8000)
- 📚 **Swagger Docs:** [http://localhost:8000/v1/docs](http://localhost:8000/v1/docs)
- 📊 **Flower (Celery):** [http://localhost:5555](http://localhost:5555)
- 📧 **MailHog:** [http://localhost:8025](http://localhost:8025)

---

## 📚 API Документация

После запуска проекта документация доступна по адресу:

👉 **[http://localhost:8000/v1/docs/](http://localhost:8000/v1/docs/)**

---

### 🗂️ Структура API

```
/api/v1/
├── auth/           # 🔐 Регистрация, логин, получение текущего пользователя
├── hotels/         # 🏨 Список отелей, поиск, детальная информация
├── rooms/          # 🚪 Информация по номерам, доступность
├── bookings/       # 📅 Создание, просмотр, отмена бронирования
├── payments/       # 💳 Обработка платежей через webhook
└── notifications/  # ✉️ Статус email-уведомлений
```

---

**Workflow процесса:**

1. **Пользователь** выполняет поиск отелей по локации и датам через `GET /api/v1/hotels/search`
2. **Выбирает** подходящий номер из доступных на эти даты
3. **Создаёт бронирование** через `POST /api/v1/bookings/` (асинхронно)
4. **Получает email-подтверждение** с деталями бронирования (Celery task)
5. **Производит оплату** через платёжный провайдер (тестовый PayPal)
6. **Webhook-событие** от провайдера поступает в `POST /api/v1/payments/webhook`
7. **Статус бронирования обновляется** автоматически в фоновом режиме
8. **Чек отправляется** на email пользователя после подтверждения платежа

## 🎯 Цели проекта

* 🚀 Практика асинхронного backend-разработки
* 🧠 Применение production-подходов
* 📦 Работа с очередями задач и мониторингом
* 🧱 Чистая архитектура и масштабируемость
* 💼 Подготовка к позиции **Junior / Junior+ Backend Developer**

---
