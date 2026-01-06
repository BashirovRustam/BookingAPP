from fastapi import FastAPI

from app.api.router import api_router

app = FastAPI()

# Подключаем единый API роутер
app.include_router(api_router)


@app.get("/")
async def read_root():
    """
    Простой health-check эндпоинт.
    """

    return {"message": "Hello, FastAPI!"}


if __name__ == "__main__":
    import uvicorn

    # Стандартный запуск приложения через uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
