import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from notification_service.celery_app import celery_app
from notification_service.config import settings


@celery_app.task(bind=True, max_retries=3)
def send_booking_email(self, email: str, booking_data: dict):
    """Send booking confirmation email."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Подтверждение бронирования #{booking_data['booking_id']}"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email

        confirm_url = booking_data.get('confirm_url', '')
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


