from fastapi import APIRouter

from app.api.v1 import (
    accounts,
    auth,
    budgets,
    categories,
    exchange_rates,
    goals,
    imports,
    recurring,
    tags,
    transactions,
    transfers,
    users,
)

router = APIRouter()
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(accounts.router)
router.include_router(transactions.router)
router.include_router(transfers.router)
router.include_router(tags.router)
router.include_router(imports.router)
router.include_router(budgets.router)
router.include_router(categories.router)
router.include_router(recurring.router)
router.include_router(exchange_rates.router)
router.include_router(goals.router)
