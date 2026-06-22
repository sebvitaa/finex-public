from fastapi import APIRouter

from backend.app.api.v1 import (
    categories,
    dashboard,
    financial_accounts,
    gmail,
    imports,
    investment_accounts,
    payables,
    people,
    receivables,
    rules,
    sessions,
    transactions,
)


api_router = APIRouter()
api_router.include_router(categories.router)
api_router.include_router(dashboard.router)
api_router.include_router(financial_accounts.router)
api_router.include_router(gmail.router)
api_router.include_router(imports.router)
api_router.include_router(investment_accounts.router)
api_router.include_router(payables.router)
api_router.include_router(people.router)
api_router.include_router(receivables.router)
api_router.include_router(rules.router)
api_router.include_router(sessions.router)
api_router.include_router(transactions.router)
