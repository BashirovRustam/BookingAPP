from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from payment_service.models import Payment, PaymentStatus


async def handle_payment_completed(body: dict, session: AsyncSession):
    resource = body.get("resource", {})
    order_id = (
        resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
    )
    capture_id = resource.get("id")

    if not order_id:
        print("⚠️ Order ID не найден в webhook")
        return

    result = await session.execute(
        select(Payment).where(Payment.paypal_order_id == order_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        print(f"❌ Платёж {order_id} не найден в БД")
        return

    if payment.status == PaymentStatus.completed:
        print(f"ℹ️ Платёж {payment.id} уже в статусе completed")
        return

    payment.status = PaymentStatus.completed
    payment.paypal_capture_id = capture_id
    await session.commit()
    print(f"✅ Платёж {payment.id} обновлён на completed")


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
    resource = body.get("resource", {})
    order_id = resource.get("id")
    print(f"✅ Заказ одобрен: {order_id}")
