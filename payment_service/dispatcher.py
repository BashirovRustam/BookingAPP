from payment_service.config import paypal_webhook_settings
from payment_service.handles_payment import (
    handle_payment_completed,
    handle_payment_refunded,
    handle_order_approved,
)


EVENT_HANDLERS = {
    paypal_webhook_settings.PAYPAL_COMPLETED_EVENT: handle_payment_completed,
    paypal_webhook_settings.PAYPAL_REFUNDED_EVENT: handle_payment_refunded,
    paypal_webhook_settings.PAYPAL_ORDER_APPROVED_EVENT: handle_order_approved,
}
