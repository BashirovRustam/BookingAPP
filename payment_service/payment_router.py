from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from payment_service.db import get_session
from payment_service.schemas import PaymentCreate, PaymentRead
from payment_service.models import Payment, PaymentStatus

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PaymentRead)
async def create_payment(
    payment_data: PaymentCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Создать новый платёж для бронирования.
    Принимает payload от монолита.
    """

    # Создаём Payment в БД
    new_payment = Payment(
        booking_id=payment_data.booking_id,
        amount=payment_data.amount,
        status=PaymentStatus.pending,
    )

    session.add(new_payment)
    await session.commit()
    await session.refresh(new_payment)

    return new_payment
