import logging
import httpx
from payment_service.notification_payload_schemas import SendReceiptPayload
from payment_service.config import settings

logger = logging.getLogger(__name__)


class NotificationClient:
    """Клиент для взаимодействия с Notification Service"""

    def __init__(self):
        self.base_url = settings.NOTIFICATION_SERVICE_URL
        self.timeout = settings.NOTIFICATION_SERVICE_TIMEOUT

    async def send_receipt(self, payload: SendReceiptPayload) -> bool:
        """
        Отправляет запрос на генерацию и отправку чека

        Args:
            payload: Данные для генерации чека

        Returns:
            True если запрос успешен, False в противном случае
        """
        url = f"{self.base_url}/api/notifications/receipt"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload.model_dump(),
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 202:  # Accepted
                    logger.info(
                        f"✅ Запрос на отправку чека отправлен в Notification Service"
                    )
                    return True
                else:
                    logger.warning(
                        f"⚠️ Notification Service вернул статус {response.status_code}: {response.text}"
                    )
                    return False

        except httpx.TimeoutException:
            logger.error(f"❌ Timeout при обращении к Notification Service")
            return False
        except httpx.RequestError as e:
            logger.error(f"❌ Ошибка при обращении к Notification Service: {e}")
            return False
        except Exception as e:
            logger.exception(
                f"❌ Неожиданная ошибка при отправке в Notification Service: {e}"
            )
            return False


notification_client = NotificationClient()
