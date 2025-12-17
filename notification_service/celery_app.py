from celery import Celery
from notification_service.config import settings

celery_app = Celery(
    "notification_service",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["notification_service.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

