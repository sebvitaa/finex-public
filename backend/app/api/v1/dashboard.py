from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.schemas import (
    DashboardCategoryTotal,
    DashboardMerchantTotal,
    DashboardOverview,
    DashboardSubscription,
    DashboardTransaction,
)
from backend.app.services.dashboard import export_dashboard_csv, get_dashboard_overview


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def overview(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
) -> DashboardOverview:
    return get_dashboard_overview(db, year=year, month=month)


@router.get("/categories", response_model=list[DashboardCategoryTotal])
def categories(
    kind: str = Query(default="expense", pattern="^(expense|income)$"),
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
) -> list[DashboardCategoryTotal]:
    dashboard = get_dashboard_overview(db, year=year, month=month)
    return dashboard.income_categories if kind == "income" else dashboard.expense_categories


@router.get("/merchants", response_model=list[DashboardMerchantTotal])
def merchants(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
) -> list[DashboardMerchantTotal]:
    return get_dashboard_overview(db, year=year, month=month).merchants


@router.get("/subscriptions", response_model=list[DashboardSubscription])
def subscriptions(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    return get_dashboard_overview(db, year=year, month=month).subscriptions


@router.get("/review", response_model=list[DashboardTransaction])
def review(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
) -> list[DashboardTransaction]:
    return get_dashboard_overview(db, year=year, month=month).review_transactions


@router.get("/export.csv")
def export_csv(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
) -> Response:
    content, filename = export_dashboard_csv(db, year=year, month=month)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
