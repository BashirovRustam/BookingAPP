from typing import Set

from pydantic_settings import BaseSettings
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    PAYPAL_CLIENT_ID: str
    PAYPAL_CLIENT_SECRET: str
    PAYPAL_API_BASE: str = "https://api-m.sandbox.paypal.com"
    PAYPAL_MODE: str = "sandbox"

    NOTIFICATION_SERVICE_URL: str = (
        "http://notification_service:8001"  # Порт вашего notification service
    )
    NOTIFICATION_SERVICE_TIMEOUT: int = 10
    
    MONOLITH_URL: str = "http://monolith:8000"  # URL monolith сервиса
    INTERNAL_SERVICE_TOKEN: str = "internal-service-token"  # Токен для внутренних сервисов

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"


settings = Settings()


# class PayPalWebhookSettings(BaseSettings):
#     PAYPAL_FAILED_EVENTS: Set[str] = {
#         "PAYMENT.CAPTURE.DENIED",
#         "PAYMENT.CAPTURE.FAILED",
#         "PAYMENT.CAPTURE.DECLINED",
#     }
#
#     PAYPAL_COMPLETED_EVENT: str = "PAYMENT.CAPTURE.COMPLETED"
#     PAYPAL_REFUNDED_EVENT: str = "PAYMENT.CAPTURE.REFUNDED"
#     PAYPAL_ORDER_APPROVED_EVENT: str = "CHECKOUT.ORDER.APPROVED"
#
#     class Config:
#         env_prefix = "PAYPAL_"


class PayPalWebhookSettings(BaseSettings):
    PAYPAL_COMPLETED_EVENT: str = "PAYMENT.CAPTURE.COMPLETED"
    PAYPAL_ORDER_APPROVED_EVENT: str = "CHECKOUT.ORDER.APPROVED"

    PAYPAL_FAILED_EVENTS: Set[str] = {
        "PAYMENT.CAPTURE.DENIED",
        "PAYMENT.CAPTURE.FAILED",
        "PAYMENT.CAPTURE.DECLINED",
    }

    class Config:
        env_prefix = "PAYPAL_"


paypal_webhook_settings = PayPalWebhookSettings()
