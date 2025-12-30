from fastapi import FastAPI, HTTPException

from notification_service import notifications_router
from notification_service.schemas import (
    BookingNotificationRequest,
    NotificationResponse,
)
from notification_service.tasks import send_booking_email

app = FastAPI(title="Notification Service")
app.include_router(notifications_router.router)


@app.post("/notify/booking", response_model=NotificationResponse)
async def send_booking_notification(request: BookingNotificationRequest):
    """Receive booking notification request and queue email task."""
    try:
        booking_data = {
            "booking_id": request.booking_id,
            "hotel_name": request.hotel_name,
            "room_name": request.room_name,
            "check_in": str(request.check_in),
            "check_out": str(request.check_out),
            "total_price": request.total_price,
            "guest_name": request.guest_name,
            "confirm_url": request.confirm_url,
        }

        task = send_booking_email.delay(request.email, booking_data)

        return NotificationResponse(
            status="queued",
            task_id=task.id,
            message="Notification task queued successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Check status of a notification task."""
    from notification_service.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}
