from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.errors import (
    AppError,
    app_error_handler,
    dbapi_error_handler,
    integrity_error_handler,
)
from app.services.recurring_service import process_due_recurring_transactions

# Cấu hình CORS
origins = [
    "http://localhost:5173",  # Cổng mặc định của Vite
    "http://127.0.0.1:5173",
    # Thêm domain production khi bạn deploy frontend, ví dụ: "https://yourdomain.com"
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        process_due_recurring_transactions,
        trigger="interval",
        minutes=1,
        id="process_due_recurring_transactions",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="1.0.0",
    lifespan=lifespan,
)

# Exception handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(DBAPIError, dbapi_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
