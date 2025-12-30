from payment_service.handles_payment import (
    handle_payment_completed,
    handle_payment_refunded,
    handle_order_approved,
    handle_payment_failed,
)

EVENT_HANDLERS = {
    "PAYMENT.CAPTURE.COMPLETED": handle_payment_completed,
    "PAYMENT.CAPTURE.DENIED": handle_payment_failed,
    "PAYMENT.CAPTURE.FAILED": handle_payment_failed,
    "PAYMENT.CAPTURE.DECLINED": handle_payment_failed,
    "PAYMENT.CAPTURE.REFUNDED": handle_payment_refunded,
    "CHECKOUT.ORDER.APPROVED": handle_order_approved,
}
