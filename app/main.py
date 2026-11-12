from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.services.recurring_service import process_due_recurring_transactions
from fastapi.middleware.cors import CORSMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Hoặc ["*"] trong môi trường dev
    allow_credentials=True,         # Cho phép gửi cookie / Authorization headers
    allow_methods=["*"],            # Cho phép GET, POST, PUT, PATCH, DELETE, OPTIONS...
    allow_headers=["*"],            # Cho phép Content-Type, Authorization...
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}