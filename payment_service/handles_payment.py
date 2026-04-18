import logging
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from payment_service.models import Payment, PaymentStatus
from payment_service.notification_client import notification_client
from payment_service.notification_payload_schemas import SendReceiptPayload
from payment_service.config import settings

logger = logging.getLogger(__name__)


async def handle_payment_completed(body: dict, session: AsyncSession):
    """
    Обработка успешного платежа PayPal.
    Обновляет статус платежа в БД и отправляет запрос на генерацию PDF чека.
    """
    resource = body.get("resource", {})
    order_id = (
        resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
    )
    capture_id = resource.get("id")

    if not order_id or not capture_id:
        logger.warning(
            "⚠️ Некорректный webhook payload: отсутствует order_id или capture_id"
        )
        logger.debug(f"Webhook body: {body}")
        return

    # Загружаем платеж
    result = await session.execute(
        select(Payment).where(Payment.paypal_order_id == order_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        logger.error(f"❌ Платёж с order_id {order_id} не найден в БД")
        return

    # Обновляем статус платежа, если он еще не completed
    if payment.status != PaymentStatus.completed:
        payment.status = PaymentStatus.completed
        payment.paypal_capture_id = capture_id
        await session.commit()
        logger.info(f"✅ Платёж {payment.id} переведён в статус completed")
    else:
        logger.info(
            f"ℹ️ Платёж {payment.id} уже имеет статус completed — отправляем чек повторно"
        )

    # Получаем email пользователя
    user_email = payment.user_email
    user_name = None

    # Если email не сохранен в Payment, пытаемся получить через внутренний API monolith
    if not user_email:
        try:
            monolith_url = settings.MONOLITH_URL
            internal_token = getattr(
                settings, "INTERNAL_SERVICE_TOKEN", "internal-service-token"
            )
            internal_url = f"{monolith_url}/api/v1/bookings/internal/{payment.booking_id}/user-email"

            async with httpx.AsyncClient(timeout=5.0) as client:
                user_resp = await client.get(
                    internal_url, headers={"X-Internal-Service": internal_token}
                )
                if user_resp.status_code == 200:
                    user_data = user_resp.json()
                    user_email = user_data.get("email")
                    user_name = user_data.get("full_name")
                    if not user_name:
                        user_name = None

                    # Сохраняем email в Payment для будущих использований
                    if user_email:
                        payment.user_email = user_email
                        await session.commit()
                        logger.info(
                            f"✅ Email пользователя сохранен в Payment {payment.id}"
                        )
                else:
                    logger.warning(
                        f"⚠️ Не удалось получить email через внутренний API: {user_resp.status_code} - {user_resp.text}"
                    )
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить email через API monolith: {e}")

    if not user_email:
        logger.error(
            f"❌ Не удалось получить email пользователя для платежа {payment.id}"
        )
        return

    # Формируем payload для Notification Service
    try:
        payload = SendReceiptPayload(
            payment_id=str(payment.id),
            order_id=payment.paypal_order_id or "",
            capture_id=payment.paypal_capture_id or "",
            amount=str(
                payment.amount / 100.0
            ),  # Конвертируем из копеек в основную валюту
            currency=payment.currency,
            user_email=user_email,
            user_name=user_name,
            description=f"Payment for booking {payment.booking_id}",
            created_at=payment.created_at.isoformat(),
            completed_at=datetime.utcnow().isoformat(),
        )

        logger.info(
            f"📤 Отправка запроса на генерацию чека для платежа {payment.id} на email {user_email}"
        )

        # Отправляем запрос через notification_client
        success = await notification_client.send_receipt(payload)

        if success:
            logger.info(
                f"✅ Запрос на отправку PDF чека для платежа {payment.id} успешно отправлен в Notification Service"
            )
        else:
            logger.error(
                f"❌ Не удалось отправить запрос на генерацию чека для платежа {payment.id}"
            )

    except Exception as e:
        logger.exception(
            f"❌ Критическая ошибка при отправке запроса на генерацию чека: {e}"
        )


async def handle_payment_failed(body: dict, session: AsyncSession):
    """Обработка события: оплата отклонена или провалилась"""
    print("🔍 Начало обработки failed события")
    print(f"🔍 Полное тело вебхука: {body}")

    resource = body.get("resource", {})
    print(f"🔍 Resource: {resource}")

    order_id = (
        resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
    )

    print(f"🔍 Извлечённый order_id: {order_id}")

    if not order_id:
        print("⚠️ Order ID не найден в webhook")
        return

    result = await session.execute(
        select(Payment).where(Payment.paypal_order_id == order_id)
    )
    payment = result.scalar_one_or_none()

    print(f"🔍 Найденный платёж: {payment}")

    if not payment:
        print(f"❌ Платёж {order_id} не найден в БД")
        return

    print(f"🔍 Текущий статус платежа: {payment.status}")

    if payment.status != PaymentStatus.pending:
        print(f"ℹ️ Платёж {payment.id} уже финализирован (статус: {payment.status})")
        return

    payment.status = PaymentStatus.failed
    payment.error_message = f"Payment {body.get('event_type')}"
    await session.commit()

    print(f"✅ COMMIT выполнен! Платёж {payment.id} обновлён на failed")


async def handle_payment_refunded(body: dict, session: AsyncSession):
    resource = body.get("resource", {})
    capture_id = resource.get("id")

    result = await session.execute(
        select(Payment).where(Payment.paypal_capture_id == capture_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        print(f"❌ Платёж с capture_id {capture_id} не найден")
        return

    payment.status = PaymentStatus.refunded
    await session.commit()
    print(f"💰 Платёж {payment.id} обновлён на REFUNDED")


async def handle_order_approved(body: dict, session: AsyncSession):
    """
    Заказ одобрен, триггерим создание платежа и чек
    """
    resource = body.get("resource", {})
    order_id = resource.get("id")
    print(f"✅ Заказ одобрен: {order_id}")

    # Пробуем вызвать обработчик completed (если заказ уже capture’нут)
    await handle_payment_completed(body, session)
