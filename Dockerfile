FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Установка зависимостей Python
COPY requirements.txt .
COPY notification_service/requirements.txt ./notification_service/
COPY payment_service/requirements.txt ./payment_service/
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r notification_service/requirements.txt && \
    pip install --no-cache-dir -r payment_service/requirements.txt

# Копирование кода
COPY . .

EXPOSE 8000 8001 8002




