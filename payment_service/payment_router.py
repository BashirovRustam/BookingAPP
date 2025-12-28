from fastapi import APIRouter, Depends, status, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from payment_service.config import paypal_webhook_settings
from payment_service.db import get_session
from payment_service.handles_payment import handle_payment_failed
from payment_service.dispatcher import EVENT_HANDLERS

from payment_service.schemas import PaymentCreate, PaymentRead, PaymentCreateResponse
from payment_service.models import Payment, PaymentStatus
from payment_service.paypal_client import create_paypal_order, capture_paypal_order
from sqlalchemy import select

from typing import Set

router = APIRouter(prefix="/payments", tags=["payments"])

processed_events: set[str] = set()


@router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=PaymentCreateResponse
)
async def create_payment(
    payment_data: PaymentCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Создать новый платёж для бронирования.
    Создаёт PayPal Order и возвращает approval_url для редиректа пользователя.
    """

    # 1. Создаём Payment в БД
    new_payment = Payment(
        booking_id=payment_data.booking_id,
        amount=payment_data.amount,
        currency=payment_data.currency,
        status=PaymentStatus.created,
    )

    session.add(new_payment)
    await session.flush()  # Получаем ID без commit

    try:
        # 2. Создаём Order в PayPal
        order_id, approval_url = await create_paypal_order(
            amount=payment_data.amount,
            currency=payment_data.currency,
            booking_id=payment_data.booking_id,
        )

        # 3. Сохраняем PayPal Order ID
        new_payment.paypal_order_id = order_id
        new_payment.status = PaymentStatus.pending

        await session.commit()
        await session.refresh(new_payment)

        # 4. Возвращаем данные с approval_url
        return PaymentCreateResponse(
            id=new_payment.id,
            booking_id=new_payment.booking_id,
            amount=new_payment.amount,
            currency=new_payment.currency,
            status=new_payment.status,
            paypal_order_id=order_id,
            approval_url=approval_url,
            created_at=new_payment.created_at,
        )

    except Exception as e:
        await session.rollback()
        new_payment.status = PaymentStatus.failed
        new_payment.error_message = str(e)
        await session.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create PayPal order: {str(e)}",
        )


@router.get("/success")
async def payment_success(
    token: str,  # PayPal передаёт order_id как параметр "token"
    session: AsyncSession = Depends(get_session),
):
    """
    Эндпоинт для возврата после успешной оплаты в PayPal.
    Захватывает платёж и обновляет статус.
    """

    try:
        # 1. Захватываем платёж в PayPal
        capture_id = await capture_paypal_order(token)

        # 2. Находим платёж в БД по paypal_order_id
        result = await session.execute(
            select(Payment).where(Payment.paypal_order_id == token)
        )
        payment = result.scalar_one_or_none()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        # 3. Обновляем статус
        payment.status = PaymentStatus.completed
        payment.paypal_capture_id = capture_id
        await session.commit()

        return {"message": "Payment successful", "capture_id": capture_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/success")
async def payment_success():
    return JSONResponse({"status": "success", "message": "Платеж одобрен"})


@router.get("/payments/cancel")
async def payment_cancel():
    return JSONResponse({"status": "cancel", "message": "Платеж отменён"})


processed_events: Set[str] = set()


@router.post("/webhook")
async def paypal_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Эндпоинт для обработки PayPal Sandbox вебхуков
    """

    body = await request.json()
    event_id = body.get("id")
    event_type = body.get("event_type")

    if not event_id or not event_type:
        raise HTTPException(status_code=400, detail="Invalid webhook data")

    print(f"🔔 Вебхук: {event_type} (ID: {event_id})")

    # Idempotency check
    if event_id in processed_events:
        print(f"⚠️ Событие {event_id} уже обработано")
        return {"status": "ok", "message": "already processed"}

    try:
        # 1️⃣ Ищем handler по event_type
        handler = EVENT_HANDLERS.get(event_type)

        if handler:
            await handler(body, session)

        # 2️⃣ Группа неуспешных платежей
        elif event_type in paypal_webhook_settings.PAYPAL_FAILED_EVENTS:
            await handle_payment_failed(body, session)

        else:
            print(f"ℹ️ Необрабатываемый event_type: {event_type}")

        processed_events.add(event_id)
        return {"status": "ok"}

    except Exception as e:
        print(f"❌ Ошибка обработки вебхука: {e}")
        # PayPal всё равно ждёт 200
        return {"status": "error"}
