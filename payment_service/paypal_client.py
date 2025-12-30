import httpx
import base64
from payment_service.config import settings


async def create_paypal_order(amount: int, currency: str, booking_id: int):
    """
    Создаёт заказ в PayPal и возвращает order_id и approval_url

    Args:
        amount: сумма в минорных единицах (копейки/центы)
        currency: валюта (USD, EUR, etc)
        booking_id: ID бронирования

    Returns:
        tuple: (order_id, approval_url)
    """

    # 1. Получаем access token
    auth = base64.b64encode(
        f"{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        # Запрос токена
        token_response = await client.post(
            f"{settings.PAYPAL_API_BASE}/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]

        # 2. Создаём заказ
        amount_value = f"{amount:.2f}"

        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": amount_value,
                    },
                    "description": f"Booking #{booking_id}",
                }
            ],
            "application_context": {
                "return_url": "http://127.0.0.1:8002/payments/success",
                "cancel_url": "http://127.0.0.1:8002/payments/cancel",
            },
        }

        order_response = await client.post(
            f"{settings.PAYPAL_API_BASE}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=order_data,
        )
        order_response.raise_for_status()
        order_json = order_response.json()

        # 3. Извлекаем order_id и approval_url
        order_id = order_json["id"]
        approval_url = next(
            link["href"] for link in order_json["links"] if link["rel"] == "approve"
        )

        return order_id, approval_url


async def capture_paypal_order(order_id: str):
    """
    Захватить (завершить) оплату в PayPal

    Args:
        order_id: PayPal Order ID

    Returns:
        capture_id: ID транзакции захвата
    """

    # Получаем access token
    auth = base64.b64encode(
        f"{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"{settings.PAYPAL_API_BASE}/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]

        # Захватываем платёж
        capture_response = await client.post(
            f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        capture_response.raise_for_status()
        capture_json = capture_response.json()

        # Извлекаем capture_id
        capture_id = capture_json["purchase_units"][0]["payments"]["captures"][0]["id"]

        return capture_id
