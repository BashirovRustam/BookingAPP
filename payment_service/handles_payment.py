from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from payment_service.models import Payment, PaymentStatus
from payment_service.notification_client import notification_client
from payment_service.notification_payload_schemas import SendReceiptPayload


async def handle_payment_completed(body: dict, session: AsyncSession):
    resource = body.get("resource", {})
    order_id = (
        resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
    )
    capture_id = resource.get("id")

    if not order_id or not capture_id:
        print("⚠️ Некорректный webhook payload")
        return

    # 1️⃣ Проверяем статус в базе
    result = await session.execute(
        select(Payment).where(Payment.paypal_order_id == order_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        print(f"❌ Платёж {order_id} не найден")
        return

    status_changed = False
    if payment.status != PaymentStatus.completed:
        payment.status = PaymentStatus.completed
        payment.paypal_capture_id = capture_id
        await session.commit()
        status_changed = True
        print(f"✅ Платёж {payment.id} переведён в completed")
    else:
        print(f"ℹ️ Платёж {payment.id} уже в статусе completed")

    # 2️⃣ Снова проверяем БД через select (чтобы быть уверенными, что коммит прошёл)
    result = await session.execute(select(Payment).where(Payment.id == payment.id))
    payment_db = result.scalar_one_or_none()
    if not payment_db:
        print(f"❌ Платёж {payment.id} исчез из БД после коммита?!")
        return

    # 3️⃣ Формируем payload для Notification Service
    receipt_payload = SendReceiptPayload(
        payment_id=payment_db.id,
        order_id=payment_db.paypal_order_id,
        capture_id=payment_db.paypal_capture_id,
        amount=str(payment_db.amount),
        currency=payment_db.currency,
        user_email=payment_db.user.email if payment_db.user else "test@example.com",
        user_name=getattr(payment_db.user, "name", None) if payment_db.user else None,
        description=payment_db.description or "Payment",
        created_at=payment_db.created_at.isoformat(),
        completed_at=datetime.utcnow().isoformat(),
    )

    # 4️⃣ Отправляем PDF через Notification Service
    notification_url = "http://notification_service:8001/api/notifications/receipt"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                notification_url, json=receipt_payload.model_dump(), timeout=10
            )
            if resp.status_code == 202:
                print(
                    f"📧 PDF чек для платёжа {payment_db.id} поставлен в очередь Notification Service"
                )
            else:
                print(f"⚠️ Notification Service вернул {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠️ Не удалось отправить PDF чек через Notification Service: {e}")


async def handle_payment_failed(body: dict, session: AsyncSession):
    """Обработка события: оплата отклонена или провалилась"""
    print(f"🔍 Начало обработки failed события")
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
