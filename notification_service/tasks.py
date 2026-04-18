import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from notification_service.celery_app import celery_app
from notification_service.config import settings
from email.mime.base import MIMEBase
from email import encoders
from notification_service.pdf_generator import generate_receipt_pdf

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def send_booking_email(self, email: str, booking_data: dict):
    """Send booking confirmation email."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Подтверждение бронирования #{booking_data['booking_id']}"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email

        confirm_url = booking_data.get("confirm_url", "")
        confirm_section = ""
        if confirm_url:
            confirm_section = f"""
            <p><b>Для подтверждения бронирования нажмите кнопку:</b></p>
            <a href="{confirm_url}" style="display:inline-block;padding:12px 24px;background-color:#4CAF50;color:white;text-decoration:none;border-radius:4px;">Подтвердить бронирование</a>
            """

        html_content = f"""
        <html>
        <body>
            <h2>Подтверждение бронирования</h2>
            <p>Уважаемый {booking_data.get('guest_name', 'гость')}!</p>
            <p>Ваше бронирование успешно оформлено.</p>
            <table border="1" cellpadding="10">
                <tr><td><b>Номер брони</b></td><td>{booking_data['booking_id']}</td></tr>
                <tr><td><b>Отель</b></td><td>{booking_data['hotel_name']}</td></tr>
                <tr><td><b>Номер</b></td><td>{booking_data['room_name']}</td></tr>
                <tr><td><b>Дата заезда</b></td><td>{booking_data['check_in']}</td></tr>
                <tr><td><b>Дата выезда</b></td><td>{booking_data['check_out']}</td></tr>
                <tr><td><b>Стоимость</b></td><td>{booking_data['total_price']} руб.</td></tr>
            </table>
            {confirm_section}
            <p>Спасибо за выбор нашего сервиса!</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, email, msg.as_string())

        return {"status": "success", "email": email}

    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def send_receipt_email(self, receipt_data: dict):
    """
    Генерирует PDF чек и отправляет на email

    Args:
        receipt_data: Словарь с данными платежа
    """
    try:
        logger.info(
            f"📧 Начинаем отправку чека для payment_id={receipt_data.get('payment_id', 'unknown')}"
        )

        # Генерируем PDF
        pdf_buffer = generate_receipt_pdf(receipt_data)

        # Создаём email
        msg = MIMEMultipart()
        msg["Subject"] = settings.RECEIPT_SUBJECT.format(
            payment_id=receipt_data["payment_id"]
        )
        msg["From"] = f"{settings.RECEIPT_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = receipt_data["user_email"]

        # HTML тело письма
        user_name = receipt_data.get("user_name", "Customer")
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2C3E50;">Payment Successful!</h2>
                <p>Dear {user_name},</p>
                <p>Thank you for your payment. Your transaction has been completed successfully.</p>

                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0;"><strong>Payment ID:</strong></td>
                            <td style="padding: 8px 0;">{receipt_data['payment_id']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Amount:</strong></td>
                            <td style="padding: 8px 0;">{receipt_data['amount']} {receipt_data['currency']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Description:</strong></td>
                            <td style="padding: 8px 0;">{receipt_data['description']}</td>
                        </tr>
                    </table>
                </div>

                <p>Please find your detailed receipt attached to this email.</p>

                <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; font-size: 14px;">
                    If you have any questions, please contact us at {settings.COMPANY_SUPPORT_EMAIL}
                </p>

                <p style="color: #7f8c8d; font-size: 14px;">
                    Best regards,<br>
                    {settings.COMPANY_NAME}
                </p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html"))

        # Прикрепляем PDF
        pdf_attachment = MIMEBase("application", "pdf")
        pdf_attachment.set_payload(pdf_buffer.read())
        encoders.encode_base64(pdf_attachment)
        pdf_attachment.add_header(
            "Content-Disposition",
            f'attachment; filename="receipt_{receipt_data["payment_id"]}.pdf"',
        )
        msg.attach(pdf_attachment)

        # Отправляем
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(
                settings.SMTP_FROM_EMAIL, receipt_data["user_email"], msg.as_string()
            )

        logger.info(f"✅ Чек успешно отправлен на {receipt_data['user_email']}")
        return {"status": "success", "email": receipt_data["user_email"]}

    except Exception as exc:
        logger.error(f"❌ Ошибка отправки чека: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)
