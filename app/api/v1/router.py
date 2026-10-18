from fastapi import APIRouter

from app.api.v1 import accounts, auth, budgets, exchange_rates, imports, recurring, transactions, users


router = APIRouter()
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(accounts.router)
router.include_router(transactions.router)
router.include_router(imports.router)
router.include_router(budgets.router)
router.include_router(recurring.router)
router.include_router(exchange_rates.router)