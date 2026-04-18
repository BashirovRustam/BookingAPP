import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from notification_service.schemas import ReceiptPayload
from notification_service.tasks import send_receipt_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.post("/receipt", status_code=202)
async def send_receipt(payload: ReceiptPayload):
    """
    Принимает данные о платеже и отправляет задачу на генерацию и отправку чека

    Args:
        payload: Данные платежа для генерации чека

    Returns:
        Статус принятия задачи
    """
    try:
        logger.info(
            f"📥 Получен запрос на отправку чека для payment_id={payload.payment_id}, email={payload.user_email}"
        )

        # Конвертируем Pydantic модель в dict
        receipt_data = payload.model_dump()

        # Отправляем задачу в Celery
        task = send_receipt_email.delay(receipt_data)

        logger.info(
            f"✅ Задача отправки чека поставлена в очередь Celery, task_id={task.id}"
        )

        return {
            "status": "accepted",
            "message": "Receipt generation task queued",
            "task_id": task.id,
            "payment_id": payload.payment_id,
            "email": payload.user_email,
        }

    except Exception as e:
        logger.error(
            f"❌ Ошибка при постановке задачи в очередь Celery: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to queue receipt task: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "ok", "service": "notification_service"}
