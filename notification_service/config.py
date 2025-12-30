from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis/Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # SMTP settings (MailHog)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@booking.local"
    SMTP_USE_TLS: bool = False

    # 🆕 Настройки для чеков
    RECEIPT_FROM_NAME: str = "Payment System"
    RECEIPT_SUBJECT: str = "Payment Receipt #{payment_id}"
    COMPANY_NAME: str = "Your Company"
    COMPANY_ADDRESS: str = "123 Business Street, City, Country"
    COMPANY_SUPPORT_EMAIL: str = "support@yourcompany.com"

    class Config:
        env_file = ".env"


settings = Settings()

