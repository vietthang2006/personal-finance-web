from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError


class AppError(HTTPException):
    def __init__(
        self,
        code: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message or code
        self.details = details or {}
        super().__init__(status_code=status_code, detail=self.message)


def round_currency(amount: Decimal, decimal_places: int) -> Decimal:
    """Rounds amount according to target currency decimal_places using ROUND_HALF_UP."""
    if decimal_places <= 0:
        target = Decimal("1")
    else:
        target = Decimal(f"1e-{decimal_places}")
    return amount.quantize(target, rounding=ROUND_HALF_UP)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    orig_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error_code": "INTEGRITY_CONFLICT",
            "message": "A database integrity constraint was violated",
            "details": {"original_error": orig_msg},
        },
    )


async def dbapi_error_handler(request: Request, exc: DBAPIError) -> JSONResponse:
    orig_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_code": "DATABASE_ERROR",
            "message": "Database query execution error",
            "details": {"original_error": orig_msg},
        },
    )

