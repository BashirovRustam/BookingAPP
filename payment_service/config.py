from typing import Set

from pydantic_settings import BaseSettings
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    PAYPAL_CLIENT_ID: str
    PAYPAL_CLIENT_SECRET: str
    PAYPAL_API_BASE: str = "https://api-m.sandbox.paypal.com"
    PAYPAL_MODE: str = "sandbox"

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"


settings = Settings()


class PayPalWebhookSettings(BaseSettings):
    PAYPAL_FAILED_EVENTS: Set[str] = {
        "PAYMENT.CAPTURE.DENIED",
        "PAYMENT.CAPTURE.FAILED",
        "PAYMENT.CAPTURE.DECLINED",
    }

    PAYPAL_COMPLETED_EVENT: str = "PAYMENT.CAPTURE.COMPLETED"
    PAYPAL_REFUNDED_EVENT: str = "PAYMENT.CAPTURE.REFUNDED"
    PAYPAL_ORDER_APPROVED_EVENT: str = "CHECKOUT.ORDER.APPROVED"

    class Config:
        env_prefix = "PAYPAL_"


paypal_webhook_settings = PayPalWebhookSettings()
