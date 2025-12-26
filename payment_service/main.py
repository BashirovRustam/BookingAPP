from fastapi import FastAPI
from contextlib import asynccontextmanager

from payment_service.db import init_db
from payment_service.payment_router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    await init_db()  # создаём таблицы, подключаемся
    yield


app = FastAPI(title="Payment Service", lifespan=lifespan)
app.include_router(router)


@app.get("/")
async def read_root():
    return {"message": "Hello, FastAPI payment!"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("payment_service.main:app", host="127.0.0.1", port=8002, reload=True)
