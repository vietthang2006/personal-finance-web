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


# Mapping from database constraint names to (HTTP status code, error_code, user-friendly message)
CONSTRAINT_ERROR_MAP: dict[str, tuple[int, str, str]] = {
    # Unique constraints
    "uq_users_email": (status.HTTP_409_CONFLICT, "EMAIL_TAKEN", "Email is already registered"),
    "uq_users_username": (status.HTTP_409_CONFLICT, "USERNAME_TAKEN", "Username is already taken"),
    "uq_accounts_user_name": (status.HTTP_409_CONFLICT, "ACCOUNT_NAME_TAKEN", "An account with this name already exists"),
    "uq_import_confirmed_file": (status.HTTP_409_CONFLICT, "FILE_ALREADY_IMPORTED", "This statement file has already been imported"),
    "uq_budget_categories": (status.HTTP_409_CONFLICT, "BUDGET_CATEGORY_DUPLICATE", "Category is already assigned to this budget"),
    "uq_budget_categories_category": (status.HTTP_409_CONFLICT, "BUDGET_CATEGORY_DUPLICATE", "Category is already assigned to this budget"),
    "uq_alert_once": (status.HTTP_409_CONFLICT, "ALERT_ALREADY_RECORDED", "Alert has already been recorded"),
    "uq_goals_user_name": (status.HTTP_409_CONFLICT, "GOAL_NAME_TAKEN", "A savings goal with this name already exists"),
    "uq_tags_user_name": (status.HTTP_409_CONFLICT, "TAG_NAME_TAKEN", "A tag with this name already exists"),
    "uq_tx_account_dedup": (status.HTTP_409_CONFLICT, "TRANSACTION_DUPLICATE", "Duplicate transaction detected"),

    # Check constraints
    "ck_accounts_non_negative": (status.HTTP_422_UNPROCESSABLE_ENTITY, "INSUFFICIENT_FUNDS", "Account has insufficient funds"),
    "ck_accounts_card_debt_limit": (status.HTTP_422_UNPROCESSABLE_ENTITY, "CREDIT_LIMIT_EXCEEDED", "Credit card limit exceeded"),
    "ck_goals_not_over": (status.HTTP_422_UNPROCESSABLE_ENTITY, "GOAL_OVER_TARGET", "Contribution amount exceeds remaining goal target"),
    "ck_goals_achieved": (status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_GOAL_STATUS", "Goal status does not match current amount or achievement date"),
    "ck_savings_goals_status": (status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_GOAL_STATUS", "Invalid savings goal status"),
    "ck_savings_goals_positive_target": (status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_TARGET_AMOUNT", "Target amount must be positive"),
    "ck_savings_goals_nonnegative_current": (status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_CURRENT_AMOUNT", "Current amount cannot be negative"),
    "ck_goal_contributions_positive_amount": (status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_CONTRIBUTION_AMOUNT", "Contribution amount must be positive"),
    "ck_budget_total_limit": (status.HTTP_422_UNPROCESSABLE_ENTITY, "BUDGET_TOTAL_EXCEEDED", "Sum of category limits exceeds total budget limit"),
    "ck_category_owner": (status.HTTP_404_NOT_FOUND, "CATEGORY_NOT_FOUND", "Category not found or does not belong to user"),
    "ck_tx_locked_by_source": (status.HTTP_409_CONFLICT, "TX_LOCKED_BY_SOURCE", "Cannot modify or delete transactions linked to savings goals or loans"),
    "ck_link_tx_match": (status.HTTP_422_UNPROCESSABLE_ENTITY, "LINKED_TRANSACTION_MISMATCH", "Transaction details do not match linked contribution requirements"),

    # Exclusion constraints
    "ex_budgets_no_overlap": (status.HTTP_409_CONFLICT, "BUDGET_OVERLAP", "Active budget periods cannot overlap for the same user"),
    "ex_budgets_active_period_per_user": (status.HTTP_409_CONFLICT, "BUDGET_OVERLAP", "Active budget periods cannot overlap for the same user"),

    # Foreign key constraints
    "fk_tx_category_kind": (status.HTTP_422_UNPROCESSABLE_ENTITY, "CATEGORY_KIND_MISMATCH", "Category kind must match transaction kind"),
    "fk_tx_subcategory": (status.HTTP_422_UNPROCESSABLE_ENTITY, "SUBCATEGORY_MISMATCH", "Subcategory does not belong to specified category"),
    "fk_transactions_category_kind": (status.HTTP_422_UNPROCESSABLE_ENTITY, "CATEGORY_KIND_MISMATCH", "Category kind must match transaction kind"),
    "fk_transactions_category_subcategory": (status.HTTP_422_UNPROCESSABLE_ENTITY, "SUBCATEGORY_MISMATCH", "Subcategory does not belong to specified category"),
    "fk_tx_account_owner": (status.HTTP_404_NOT_FOUND, "ACCOUNT_NOT_FOUND", "Account not found"),
    "fk_transactions_account_owner": (status.HTTP_404_NOT_FOUND, "ACCOUNT_NOT_FOUND", "Account not found"),
    "fk_savings_goals_user": (status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "User not found"),
    "fk_goal_contributions_goal": (status.HTTP_404_NOT_FOUND, "GOAL_NOT_FOUND", "Savings goal not found"),
    "goal_contributions_goal_id_fkey": (status.HTTP_404_NOT_FOUND, "GOAL_NOT_FOUND", "Savings goal not found"),
    "goal_contributions_transaction_id_fkey": (status.HTTP_409_CONFLICT, "TX_LOCKED_BY_SOURCE", "Cannot delete transaction linked to savings goal"),
}


def _extract_constraint_name(exc: IntegrityError) -> str | None:
    orig = getattr(exc, "orig", None)
    if orig is not None:
        diag = getattr(orig, "diag", None)
        if diag is not None:
            cname = getattr(diag, "constraint_name", None)
            if cname:
                return str(cname)

    exc_str = str(exc)
    for cname in CONSTRAINT_ERROR_MAP:
        if cname in exc_str:
            return cname

    return None


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
    cname = _extract_constraint_name(exc)
    if cname and cname in CONSTRAINT_ERROR_MAP:
        status_code, error_code, message = CONSTRAINT_ERROR_MAP[cname]
        return JSONResponse(
            status_code=status_code,
            content={
                "error_code": error_code,
                "message": message,
                "details": {},
            },
        )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error_code": "INTEGRITY_CONFLICT",
            "message": "A database integrity constraint was violated",
            "details": {},
        },
    )


async def dbapi_error_handler(request: Request, exc: DBAPIError) -> JSONResponse:
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None)
    if sqlstate in ("40001", "40P01"):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error_code": "TRY_AGAIN",
                "message": "Transaction conflict or serialization failure; please retry",
                "details": {},
            },
        )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_code": "DATABASE_ERROR",
            "message": "Database query execution error",
            "details": {},
        },
    )
