from __future__ import annotations

import csv
from io import StringIO
from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import Category, FinancialAccount, FinancialAccountSnapshot, InvestmentAccount, InvestmentMovement, Payable, Receivable, Transaction, TransactionSplit
from backend.app.schemas.dashboard import (
    DashboardBudgetProgress,
    DashboardCategoryTotal,
    DashboardDailyHeatmapPoint,
    DashboardDailyPoint,
    DashboardFinancialAccount,
    DashboardInsight,
    DashboardInvestmentAccount,
    DashboardMerchantTotal,
    DashboardMetrics,
    DashboardObligationPersonTotal,
    DashboardOverview,
    DashboardPeriod,
    DashboardPeriodComparison,
    DashboardPersonTotal,
    DashboardReceivable,
    DashboardSubscription,
    DashboardTransaction,
)


EXPENSE_TYPES = {"expense", "subscription", "transfer_out"}
INCOME_TYPES = {"income", "transfer_in", "refund"}
BALANCE_ONLY_TYPES = {"investment", "disinvestment", "receivable_payment", "payable_payment", "internal_transfer"}
EXCLUDED_STATUSES = {"ignored", "duplicate"}
OPEN_RECEIVABLE_STATUSES = {"pending_payment", "partially_paid", "overdue"}
OPEN_PAYABLE_STATUSES = {"pending_payment", "partially_paid", "overdue"}
SUPERMARKET_NAMES = ("lider", "líder", "jumbo", "unimarc", "tottus")
BUDGETS_BY_CATEGORY = {
    "Supermercado": Decimal("250000"),
    "Golosinas": Decimal("40000"),
    "Aseo y limpieza": Decimal("35000"),
    "Comida": Decimal("180000"),
    "Transporte": Decimal("80000"),
    "Suscripciones": Decimal("50000"),
}


@dataclass
class CategoryBucket:
    category_id: int | None
    name: str
    color: str
    amount: Decimal = Decimal("0")


@dataclass
class PeriodAggregation:
    expense: Decimal
    income: Decimal
    daily_expense: dict[date, Decimal]
    daily_income: dict[date, Decimal]
    expense_categories: dict[str, CategoryBucket]
    income_categories: dict[str, CategoryBucket]
    merchants: dict[str, DashboardMerchantTotal]


def money(value: Decimal | int | str = Decimal("0")) -> Decimal:
    return Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def money_for_currency(value: Decimal | int | str = Decimal("0"), currency: str = "CLP") -> Decimal:
    quantizer = Decimal("1") if currency == "CLP" else Decimal("0.01")
    return Decimal(value).quantize(quantizer, rounding=ROUND_HALF_UP)


def _transaction_clp_amount(transaction: Transaction) -> Decimal:
    if transaction.amount_clp is not None:
        return money(transaction.amount_clp)
    if transaction.currency == "CLP":
        return money(transaction.amount)
    return Decimal("0")


def _account_signed_amount(transaction: Transaction, account: FinancialAccount) -> Decimal:
    amount = transaction.signed_amount or Decimal("0")
    if account.account_type == "credit_card" and transaction.transaction_type == "payable_payment":
        return abs(transaction.amount)
    return amount


def _incoming_transfer_amount(transaction: Transaction, account: FinancialAccount) -> Decimal:
    """Amount an internal transfer credits to ``account`` as its destination leg."""
    if (
        transaction.transaction_type != "internal_transfer"
        or transaction.destination_account_id != account.id
        or (transaction.destination_currency or transaction.currency) != account.currency
    ):
        return Decimal("0")
    amount = transaction.destination_amount if transaction.destination_amount is not None else transaction.amount
    return abs(amount or Decimal("0"))


def _resolve_period(year: int | None, month: int | None) -> tuple[date, int, int, date, date]:
    today = datetime.now(timezone.utc).date()
    resolved_year = year or today.year
    resolved_month = month or today.month
    start = date(resolved_year, resolved_month, 1)
    end = date(resolved_year, resolved_month, monthrange(resolved_year, resolved_month)[1])
    return today, resolved_year, resolved_month, start, end


def _previous_period(year: int, month: int) -> tuple[int, int, date, date]:
    if month == 1:
        previous_year = year - 1
        previous_month = 12
    else:
        previous_year = year
        previous_month = month - 1
    start = date(previous_year, previous_month, 1)
    end = date(previous_year, previous_month, monthrange(previous_year, previous_month)[1])
    return previous_year, previous_month, start, end


def _as_comparable_datetime(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _in_datetime_range(value: datetime, start: datetime, end: datetime) -> bool:
    comparable = _as_comparable_datetime(value)
    return comparable is not None and start <= comparable <= end


def _transactions_in_period(transactions: list[Transaction], start: date, end: date) -> list[Transaction]:
    return [
        transaction
        for transaction in transactions
        if transaction.status not in EXCLUDED_STATUSES and start <= transaction.occurred_at.date() <= end
    ]


def _aggregate_period(transactions: list[Transaction]) -> PeriodAggregation:
    daily_expense: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    daily_income: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    expense_categories: dict[str, CategoryBucket] = {}
    income_categories: dict[str, CategoryBucket] = {}
    merchants: dict[str, DashboardMerchantTotal] = {}
    period_expense = Decimal("0")
    period_income = Decimal("0")

    for transaction in transactions:
        occurred_on = transaction.occurred_at.date()
        if transaction.transaction_type in EXPENSE_TYPES:
            amount = _transaction_clp_amount(transaction)
            if amount <= Decimal("0"):
                continue
            period_expense += amount
            daily_expense[occurred_on] += amount
            _add_merchant(merchants, transaction, amount)
            for category_id, name, color, split_amount in _expense_category_parts(transaction):
                key = f"{category_id}:{name}"
                bucket = expense_categories.setdefault(key, CategoryBucket(category_id, name, color))
                bucket.amount += money(split_amount)
        elif transaction.transaction_type in INCOME_TYPES:
            amount = _transaction_clp_amount(transaction)
            if amount <= Decimal("0"):
                continue
            period_income += amount
            daily_income[occurred_on] += amount
            category = transaction.category
            key = f"{category.id if category else 'none'}:{category.name if category else 'Sin categoria'}"
            bucket = income_categories.setdefault(
                key,
                CategoryBucket(
                    category.id if category else None,
                    category.name if category else "Sin categoria",
                    category.color if category else "#71717A",
                ),
            )
            bucket.amount += amount

    return PeriodAggregation(
        expense=period_expense,
        income=period_income,
        daily_expense=daily_expense,
        daily_income=daily_income,
        expense_categories=expense_categories,
        income_categories=income_categories,
        merchants=merchants,
    )


def get_dashboard_overview(db: Session, year: int | None = None, month: int | None = None) -> DashboardOverview:
    today, year, month, start, end = _resolve_period(year, month)
    previous_year, previous_month, previous_start, previous_end = _previous_period(year, month)

    transactions = _load_transactions(db)
    receivables = _load_receivables(db)
    payables = _load_payables(db)
    budget_categories = _load_budget_categories(db)
    financial_accounts = _load_financial_accounts(db)
    investment_accounts = _load_investment_accounts(db)
    investment_movements = _load_investment_movements(db)

    monthly_transactions = _transactions_in_period(transactions, start, end)
    previous_transactions = _transactions_in_period(transactions, previous_start, previous_end)
    latest_transaction_date = max((transaction.occurred_at.date() for transaction in monthly_transactions), default=start)
    if year == today.year and month == today.month:
        visible_end = min(end, max(today, latest_transaction_date))
    else:
        visible_end = end
    elapsed_days = max((visible_end - start).days + 1, 1)
    open_receivables = [
        receivable
        for receivable in receivables
        if receivable.status in OPEN_RECEIVABLE_STATUSES and receivable.remaining_amount > Decimal("0")
    ]
    open_payables = [
        payable
        for payable in payables
        if payable.status in OPEN_PAYABLE_STATUSES and payable.remaining_amount > Decimal("0")
    ]

    current_aggregation = _aggregate_period(monthly_transactions)
    previous_aggregation = _aggregate_period(previous_transactions)
    financial_account_summaries = _financial_account_summaries(financial_accounts, transactions, start, end)
    investment_account_summaries = _investment_account_summaries(investment_accounts, investment_movements, start, end)

    daily = _daily_points(start, visible_end, current_aggregation.daily_expense, current_aggregation.daily_income)
    pending_receivables_total = sum((money(receivable.remaining_amount) for receivable in open_receivables), Decimal("0"))
    overdue_count = sum(1 for receivable in open_receivables if _is_overdue(receivable, today))
    upcoming_count = sum(1 for receivable in open_receivables if _is_upcoming(receivable, today))

    metrics = DashboardMetrics(
        liquid_balance=_liquid_balance(financial_account_summaries),
        investment_balance=sum((money(account.current_value) for account in investment_account_summaries if account.currency == "CLP"), Decimal("0")),
        month_expense=money(current_aggregation.expense),
        month_income=money(current_aggregation.income),
        net_balance=money(current_aggregation.income - current_aggregation.expense),
        today_expense=money(current_aggregation.daily_expense.get(today, Decimal("0"))),
        daily_average_expense=money(current_aggregation.expense / elapsed_days),
        projected_month_expense=money((current_aggregation.expense / elapsed_days) * monthrange(year, month)[1]),
        review_count=sum(1 for transaction in monthly_transactions if transaction.status == "needs_review"),
        pending_receivables=money(pending_receivables_total),
        overdue_receivables=overdue_count,
        upcoming_receivables=upcoming_count,
    )
    expense_categories = _category_totals(current_aggregation.expense_categories)
    income_categories = _category_totals(current_aggregation.income_categories)

    return DashboardOverview(
        generated_at=datetime.now(timezone.utc),
        period=DashboardPeriod(from_date=start, to_date=end, label=f"{month:02d}/{year}"),
        metrics=metrics,
        daily=daily,
        daily_heatmap=_daily_heatmap(start, visible_end, current_aggregation.daily_expense),
        period_comparison=_period_comparison(
            current_aggregation,
            previous_aggregation,
            previous_label=f"{previous_month:02d}/{previous_year}",
        ),
        insights=_dashboard_insights(
            monthly_transactions,
            previous_transactions,
            current_aggregation,
            previous_aggregation,
            metrics,
            visible_end,
        ),
        expense_categories=expense_categories,
        income_categories=income_categories,
        merchants=sorted(current_aggregation.merchants.values(), key=lambda item: item.amount, reverse=True)[:10],
        budget_progress=_budget_progress(budget_categories, expense_categories),
        class_income_by_person=_class_income_by_person(monthly_transactions),
        receivables_by_person=_receivables_by_person(open_receivables, today),
        payables_by_person=_payables_by_person(open_payables, today),
        mixed_purchase_totals=_mixed_purchase_totals(monthly_transactions),
        recent_transactions=[_dashboard_transaction(transaction) for transaction in monthly_transactions[:8]],
        review_transactions=[
            _dashboard_transaction(transaction)
            for transaction in monthly_transactions
            if transaction.status == "needs_review"
        ][:8],
        unallocated_supermarkets=[
            _dashboard_transaction(transaction)
            for transaction in monthly_transactions
            if transaction.transaction_type in EXPENSE_TYPES and not transaction.splits and _looks_like_supermarket(transaction)
        ][:8],
        pending_receivables=[_dashboard_receivable(receivable) for receivable in open_receivables[:8]],
        subscriptions=_detect_subscriptions(transactions),
        financial_accounts=financial_account_summaries,
        investment_accounts=investment_account_summaries,
        unassigned_account_transactions=[
            _dashboard_transaction(transaction)
            for transaction in monthly_transactions
            if transaction.transaction_type not in BALANCE_ONLY_TYPES
            and transaction.financial_account_id is None
            and transaction.investment_account_id is None
        ][:8],
    )


def export_dashboard_csv(db: Session, year: int | None = None, month: int | None = None) -> tuple[str, str]:
    _, year, month, start, end = _resolve_period(year, month)
    transactions = _transactions_in_period(_load_transactions(db), start, end)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "occurred_at",
            "type",
            "status",
            "merchant_or_counterparty",
            "description",
            "category",
            "amount",
            "currency",
            "amount_clp",
            "original_amount",
            "original_currency",
            "relationship",
            "person",
            "financial_account",
            "investment_account",
            "split_category",
            "split_label",
            "split_amount",
        ]
    )
    for transaction in sorted(transactions, key=lambda item: (item.occurred_at, item.id)):
        base = [
            transaction.id,
            transaction.occurred_at.isoformat(),
            transaction.transaction_type,
            transaction.status,
            transaction.merchant_name or transaction.counterparty or "",
            transaction.description or "",
            transaction.category.name if transaction.category else "",
            money_for_currency(transaction.amount, transaction.currency),
            transaction.currency,
            money(transaction.amount_clp) if transaction.amount_clp is not None else "",
            transaction.original_amount or "",
            transaction.original_currency or "",
            transaction.relationship_category,
            transaction.person.name if transaction.person else "",
            transaction.financial_account.name if transaction.financial_account else "",
            transaction.investment_account.name if transaction.investment_account else "",
        ]
        if transaction.splits:
            for split in transaction.splits:
                writer.writerow(
                    base
                    + [
                        split.category.name if split.category else "",
                        split.label or "",
                        _category_part_amount(transaction, split.amount),
                    ]
                )
        else:
            writer.writerow(base + ["", "", ""])

    return output.getvalue(), f"finex-dashboard-{year}-{month:02d}.csv"


def _load_transactions(db: Session) -> list[Transaction]:
    query = (
        select(Transaction)
        .options(
            selectinload(Transaction.category),
            selectinload(Transaction.financial_account),
            selectinload(Transaction.investment_account),
            selectinload(Transaction.person),
            selectinload(Transaction.splits).selectinload(TransactionSplit.category),
        )
        .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
    )
    return list(db.scalars(query).all())


def _load_receivables(db: Session) -> list[Receivable]:
    query = select(Receivable).options(selectinload(Receivable.person)).order_by(Receivable.due_at, Receivable.id)
    return list(db.scalars(query).all())


def _load_payables(db: Session) -> list[Payable]:
    query = select(Payable).options(selectinload(Payable.person)).order_by(Payable.due_at, Payable.id)
    return list(db.scalars(query).all())


def _load_budget_categories(db: Session) -> list[Category]:
    query = select(Category).where(Category.name.in_(BUDGETS_BY_CATEGORY.keys())).order_by(Category.sort_order, Category.name)
    return list(db.scalars(query).all())


def _load_financial_accounts(db: Session) -> list[FinancialAccount]:
    query = (
        select(FinancialAccount)
        .options(selectinload(FinancialAccount.snapshots))
        .where(FinancialAccount.is_active.is_(True))
        .order_by(FinancialAccount.name)
    )
    return list(db.scalars(query).all())


def _load_investment_accounts(db: Session) -> list[InvestmentAccount]:
    query = select(InvestmentAccount).where(InvestmentAccount.is_active.is_(True)).order_by(InvestmentAccount.name)
    return list(db.scalars(query).all())


def _load_investment_movements(db: Session) -> list[InvestmentMovement]:
    query = select(InvestmentMovement).order_by(InvestmentMovement.occurred_at.desc(), InvestmentMovement.id.desc())
    return list(db.scalars(query).all())


def _expense_category_parts(transaction: Transaction) -> list[tuple[int | None, str, str, Decimal]]:
    if transaction.splits:
        parts = []
        for split in transaction.splits:
            category = split.category
            parts.append(
                (
                    category.id if category else None,
                    category.name if category else split.label or "Sin categoria",
                    category.color if category else "#71717A",
                    _category_part_amount(transaction, split.amount),
                )
            )
        return parts

    category = transaction.category
    return [
        (
            category.id if category else None,
            category.name if category else "Sin categoria",
            category.color if category else "#71717A",
            _transaction_clp_amount(transaction),
        )
    ]


def _category_part_amount(transaction: Transaction, amount: Decimal) -> Decimal:
    if transaction.amount <= Decimal("0"):
        return Decimal("0")
    if transaction.amount_clp is None:
        return money(amount) if transaction.currency == "CLP" else Decimal("0")
    if transaction.currency == "CLP":
        return money(amount)
    return money((amount * transaction.amount_clp) / transaction.amount)


def _add_merchant(merchants: dict[str, DashboardMerchantTotal], transaction: Transaction, amount: Decimal) -> None:
    merchant = transaction.merchant_name or transaction.counterparty or "Sin comercio"
    current = merchants.setdefault(merchant, DashboardMerchantTotal(name=merchant, amount=Decimal("0"), count=0))
    current.amount = money(current.amount + amount)
    current.count += 1


def _daily_points(
    start: date,
    end: date,
    daily_expense: dict[date, Decimal],
    daily_income: dict[date, Decimal],
) -> list[DashboardDailyPoint]:
    points = []
    current = start
    while current <= end:
        expense = money(daily_expense.get(current, Decimal("0")))
        income = money(daily_income.get(current, Decimal("0")))
        points.append(
            DashboardDailyPoint(
                date=current,
                label=f"{current.day:02d} {current.strftime('%b').lower()}",
                expense=expense,
                income=income,
                balance=money(income - expense),
            )
        )
        current += timedelta(days=1)
    return points


def _daily_heatmap(
    start: date,
    end: date,
    daily_expense: dict[date, Decimal],
) -> list[DashboardDailyHeatmapPoint]:
    max_expense = max((money(amount) for amount in daily_expense.values()), default=Decimal("0"))
    points: list[DashboardDailyHeatmapPoint] = []
    current = start
    while current <= end:
        expense = money(daily_expense.get(current, Decimal("0")))
        intensity = float(expense / max_expense) if max_expense > Decimal("0") else 0
        points.append(
            DashboardDailyHeatmapPoint(
                date=current,
                day=current.day,
                weekday=current.isoweekday(),
                expense=expense,
                intensity=min(1, intensity),
            )
        )
        current += timedelta(days=1)
    return points


def _category_totals(buckets: dict[str, CategoryBucket]) -> list[DashboardCategoryTotal]:
    return [
        DashboardCategoryTotal(
            category_id=bucket.category_id,
            name=bucket.name,
            color=bucket.color,
            amount=money(bucket.amount),
        )
        for bucket in sorted(buckets.values(), key=lambda item: item.amount, reverse=True)
        if bucket.amount > Decimal("0")
    ][:10]


def _period_comparison(
    current: PeriodAggregation,
    previous: PeriodAggregation,
    previous_label: str,
) -> DashboardPeriodComparison:
    current_net = current.income - current.expense
    previous_net = previous.income - previous.expense
    return DashboardPeriodComparison(
        previous_label=previous_label,
        previous_expense=money(previous.expense),
        expense_delta=money(current.expense - previous.expense),
        expense_delta_percent=_percent_delta(current.expense, previous.expense),
        previous_income=money(previous.income),
        income_delta=money(current.income - previous.income),
        income_delta_percent=_percent_delta(current.income, previous.income),
        previous_net_balance=money(previous_net),
        net_balance_delta=money(current_net - previous_net),
    )


def _percent_delta(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == Decimal("0"):
        return None
    return money(((current - previous) / previous) * Decimal("100"))


def _dashboard_insights(
    monthly_transactions: list[Transaction],
    previous_transactions: list[Transaction],
    current: PeriodAggregation,
    previous: PeriodAggregation,
    metrics: DashboardMetrics,
    visible_end: date,
) -> list[DashboardInsight]:
    insights: list[DashboardInsight] = []
    daily_average = metrics.daily_average_expense
    high_day_floor = max(daily_average * Decimal("1.8"), Decimal("30000.00"))
    for occurred_on, amount in sorted(current.daily_expense.items(), key=lambda item: item[1], reverse=True):
        if amount >= high_day_floor:
            insights.append(
                DashboardInsight(
                    kind="daily_spike",
                    title="Dia de gasto alto",
                    detail=f"{occurred_on.isoformat()} supera tu promedio diario del periodo.",
                    amount=money(amount),
                    severity="warning",
                )
            )
            break

    previous_merchants = {
        _merchant_key(transaction)
        for transaction in previous_transactions
        if transaction.transaction_type in EXPENSE_TYPES and _merchant_key(transaction)
    }
    for merchant in sorted(current.merchants.values(), key=lambda item: item.amount, reverse=True):
        if merchant.name.lower() not in previous_merchants and merchant.amount >= max(current.expense * Decimal("0.15"), Decimal("25000.00")):
            insights.append(
                DashboardInsight(
                    kind="new_merchant",
                    title="Comercio nuevo relevante",
                    detail=f"{merchant.name} aparece fuerte este mes y no estaba en {visible_end.month - 1 if visible_end.month > 1 else 12:02d}.",
                    amount=money(merchant.amount),
                    severity="info",
                )
            )
            break

    previous_by_category = {bucket.name: bucket.amount for bucket in previous.expense_categories.values()}
    for bucket in sorted(current.expense_categories.values(), key=lambda item: item.amount, reverse=True):
        previous_amount = previous_by_category.get(bucket.name, Decimal("0"))
        delta = bucket.amount - previous_amount
        if previous_amount > Decimal("0") and delta >= max(previous_amount * Decimal("0.5"), Decimal("15000.00")):
            insights.append(
                DashboardInsight(
                    kind="category_growth",
                    title="Categoria creciendo",
                    detail=f"{bucket.name} subio respecto del mes anterior.",
                    amount=money(delta),
                    severity="warning",
                )
            )
            break

    if metrics.projected_month_expense > current.expense and metrics.projected_month_expense >= current.expense * Decimal("1.25"):
        insights.append(
            DashboardInsight(
                kind="projection",
                title="Proyeccion sobre ritmo actual",
                detail="Si mantienes el promedio diario, el gasto mensual terminaria bastante mas alto que lo registrado hasta ahora.",
                amount=metrics.projected_month_expense,
                severity="info",
            )
        )

    if not insights and monthly_transactions:
        insights.append(
            DashboardInsight(
                kind="stable",
                title="Sin alertas fuertes",
                detail="No veo saltos grandes por dia, comercio o categoria en este periodo.",
                severity="success",
            )
        )
    return insights[:8]


def _merchant_key(transaction: Transaction) -> str:
    return (transaction.merchant_name or transaction.counterparty or "").strip().lower()


def _budget_progress(
    budget_categories: list[Category],
    expense_categories: list[DashboardCategoryTotal],
) -> list[DashboardBudgetProgress]:
    spent_by_name = {category.name: money(category.amount) for category in expense_categories}
    progress: list[DashboardBudgetProgress] = []
    for category in budget_categories:
        budget = BUDGETS_BY_CATEGORY[category.name]
        spent = spent_by_name.get(category.name, Decimal("0"))
        usage_percent = Decimal("0") if budget == Decimal("0") else money((spent / budget) * Decimal("100"))
        status = "ok"
        if usage_percent >= Decimal("100"):
            status = "over"
        elif usage_percent >= Decimal("80"):
            status = "watch"
        progress.append(
            DashboardBudgetProgress(
                category_id=category.id,
                name=category.name,
                color=category.color,
                budget_amount=money(budget),
                spent_amount=money(spent),
                remaining_amount=money(budget - spent),
                usage_percent=usage_percent,
                status=status,
            )
        )
    return progress


def _class_income_by_person(transactions: list[Transaction]) -> list[DashboardPersonTotal]:
    grouped: dict[str, DashboardPersonTotal] = {}
    for transaction in transactions:
        if transaction.transaction_type not in INCOME_TYPES or not _looks_like_class_income(transaction):
            continue
        person_id = transaction.person_id
        person_name = transaction.person.name if transaction.person else transaction.counterparty or "Sin persona"
        amount = _transaction_clp_amount(transaction)
        if amount <= Decimal("0"):
            continue
        key = f"{person_id}:{person_name}"
        total = grouped.setdefault(key, DashboardPersonTotal(person_id=person_id, person_name=person_name))
        total.amount = money(total.amount + amount)
        total.count += 1
    return sorted(grouped.values(), key=lambda item: item.amount, reverse=True)[:8]


def _looks_like_class_income(transaction: Transaction) -> bool:
    text = " ".join(
        value.lower()
        for value in [
            transaction.category.name if transaction.category else None,
            transaction.description,
            transaction.counterparty,
            transaction.merchant_name,
        ]
        if value
    )
    return "clase" in text or "alumno" in text


def _receivables_by_person(receivables: list[Receivable], today: date) -> list[DashboardObligationPersonTotal]:
    grouped: dict[int, DashboardObligationPersonTotal] = {}
    for receivable in receivables:
        total = grouped.setdefault(
            receivable.person_id,
            DashboardObligationPersonTotal(person_id=receivable.person_id, person_name=receivable.person.name),
        )
        total.amount = money(total.amount + receivable.remaining_amount)
        total.count += 1
        total.overdue_count += 1 if _is_overdue(receivable, today) else 0
        total.next_due_at = _earliest_date(total.next_due_at, receivable.due_at)
    return sorted(grouped.values(), key=lambda item: item.amount, reverse=True)[:8]


def _payables_by_person(payables: list[Payable], today: date) -> list[DashboardObligationPersonTotal]:
    grouped: dict[int, DashboardObligationPersonTotal] = {}
    for payable in payables:
        total = grouped.setdefault(
            payable.person_id,
            DashboardObligationPersonTotal(person_id=payable.person_id, person_name=payable.person.name),
        )
        total.amount = money(total.amount + payable.remaining_amount)
        total.count += 1
        total.overdue_count += 1 if _payable_is_overdue(payable, today) else 0
        total.next_due_at = _earliest_date(total.next_due_at, payable.due_at)
    return sorted(grouped.values(), key=lambda item: item.amount, reverse=True)[:8]


def _earliest_date(current: datetime | None, candidate: datetime | None) -> datetime | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    return min(current, candidate)


def _mixed_purchase_totals(transactions: list[Transaction]) -> list[DashboardCategoryTotal]:
    buckets: dict[str, CategoryBucket] = {}
    for transaction in transactions:
        if transaction.transaction_type not in EXPENSE_TYPES or not transaction.splits:
            continue
        for category_id, name, color, split_amount in _expense_category_parts(transaction):
            key = f"{category_id}:{name}"
            bucket = buckets.setdefault(key, CategoryBucket(category_id, name, color))
            bucket.amount += money(split_amount)
    return _category_totals(buckets)


def _dashboard_transaction(transaction: Transaction) -> DashboardTransaction:
    category = transaction.category
    return DashboardTransaction(
        id=transaction.id,
        occurred_at=transaction.occurred_at,
        amount=money_for_currency(transaction.amount, transaction.currency),
        currency=transaction.currency,
        original_amount=money_for_currency(transaction.original_amount, transaction.original_currency or transaction.currency) if transaction.original_amount is not None else None,
        original_currency=transaction.original_currency,
        amount_clp=money(transaction.amount_clp) if transaction.amount_clp is not None else None,
        exchange_rate=transaction.exchange_rate,
        currency_detection_confidence=transaction.currency_detection_confidence,
        currency_detection_reason=transaction.currency_detection_reason,
        merchant_name=transaction.merchant_name,
        counterparty=transaction.counterparty,
        description=transaction.description,
        category_name=category.name if category else None,
        category_color=category.color if category else None,
        transaction_type=transaction.transaction_type,
        status=transaction.status,
        has_splits=bool(transaction.splits),
    )


def _dashboard_receivable(receivable: Receivable) -> DashboardReceivable:
    return DashboardReceivable(
        id=receivable.id,
        person_name=receivable.person.name,
        title=receivable.title,
        remaining_amount=money(receivable.remaining_amount),
        currency=receivable.currency,
        due_at=receivable.due_at,
        status=receivable.status,
    )


def _financial_account_summaries(
    accounts: list[FinancialAccount],
    transactions: list[Transaction],
    start: date,
    end: date,
) -> list[DashboardFinancialAccount]:
    summaries: list[DashboardFinancialAccount] = []
    end_dt = datetime.combine(end, datetime.max.time())
    start_dt = datetime.combine(start, datetime.min.time())
    for account in accounts:
        snapshot = _latest_snapshot(account, end_dt)
        base = snapshot.balance if snapshot else account.opening_balance
        since = _as_comparable_datetime(snapshot.captured_at) if snapshot else None
        account_transactions = [
            transaction
            for transaction in transactions
            if transaction.financial_account_id == account.id
            and transaction.status not in EXCLUDED_STATUSES
            and transaction.currency == account.currency
            and (_as_comparable_datetime(transaction.occurred_at) or datetime.min) <= end_dt
            and (since is None or (_as_comparable_datetime(transaction.occurred_at) or datetime.min) > since)
        ]
        incoming_transfers = [
            transaction
            for transaction in transactions
            if transaction.destination_account_id == account.id
            and transaction.transaction_type == "internal_transfer"
            and transaction.status not in EXCLUDED_STATUSES
            and (transaction.destination_currency or transaction.currency) == account.currency
            and (_as_comparable_datetime(transaction.occurred_at) or datetime.min) <= end_dt
            and (since is None or (_as_comparable_datetime(transaction.occurred_at) or datetime.min) > since)
        ]
        balance = base + sum((_account_signed_amount(transaction, account) for transaction in account_transactions), Decimal("0"))
        balance += sum((_incoming_transfer_amount(transaction, account) for transaction in incoming_transfers), Decimal("0"))
        monthly = [
            transaction
            for transaction in transactions
            if transaction.financial_account_id == account.id
            and transaction.status not in EXCLUDED_STATUSES
            and transaction.currency == account.currency
            and _in_datetime_range(transaction.occurred_at, start_dt, end_dt)
        ]
        monthly_incoming = [
            transaction
            for transaction in transactions
            if transaction.destination_account_id == account.id
            and transaction.transaction_type == "internal_transfer"
            and transaction.status not in EXCLUDED_STATUSES
            and (transaction.destination_currency or transaction.currency) == account.currency
            and _in_datetime_range(transaction.occurred_at, start_dt, end_dt)
        ]
        month_delta = sum((_account_signed_amount(transaction, account) for transaction in monthly), Decimal("0"))
        month_delta += sum((_incoming_transfer_amount(transaction, account) for transaction in monthly_incoming), Decimal("0"))
        used_credit = None
        available_credit = None
        statement_amount = account.statement_amount
        if account.account_type == "credit_card":
            used_credit = account.used_credit_amount
            if used_credit is None:
                used_credit = abs(balance) if balance < Decimal("0") else Decimal("0")
            if account.credit_limit_amount is not None:
                available_credit = account.available_credit_amount
                if available_credit is None:
                    available_credit = max(account.credit_limit_amount - used_credit, Decimal("0"))
            calculated_statement = sum(
                (abs(_account_signed_amount(transaction, account)) for transaction in monthly if _account_signed_amount(transaction, account) < Decimal("0")),
                Decimal("0"),
            )
            if not account.statement_amount_overridden:
                statement_amount = calculated_statement
        summaries.append(
            DashboardFinancialAccount(
                account_id=account.id,
                name=account.name,
                institution=account.institution,
                account_type=account.account_type,
                last_four=account.last_four,
                currency=account.currency,
                balance=money_for_currency(balance, account.currency),
                month_delta=money_for_currency(month_delta, account.currency),
                transaction_count=len(monthly),
                credit_limit_amount=money_for_currency(account.credit_limit_amount, account.credit_limit_currency or account.currency) if account.credit_limit_amount is not None else None,
                credit_limit_currency=account.credit_limit_currency,
                used_credit_amount=money_for_currency(used_credit, account.credit_limit_currency or account.currency) if used_credit is not None else None,
                available_credit_amount=money_for_currency(available_credit, account.credit_limit_currency or account.currency) if available_credit is not None else None,
                billing_cycle_day=account.billing_cycle_day,
                payment_due_day=account.payment_due_day,
                statement_amount=money_for_currency(statement_amount, account.statement_currency or account.currency) if statement_amount is not None else None,
                statement_currency=account.statement_currency,
                statement_amount_overridden=account.statement_amount_overridden,
                card_art_variant=account.card_art_variant,
                visual_group=account.visual_group,
            )
        )
    return summaries


def _liquid_balance(accounts: list[DashboardFinancialAccount]) -> Decimal:
    return sum((money(account.balance) for account in accounts if account.account_type != "credit_card" and account.currency == "CLP"), Decimal("0"))


def _latest_snapshot(account: FinancialAccount, end_dt: datetime) -> FinancialAccountSnapshot | None:
    eligible = [
        snapshot
        for snapshot in account.snapshots
        if (_as_comparable_datetime(snapshot.captured_at) or datetime.min) <= end_dt
    ]
    return max(eligible, key=lambda snapshot: (_as_comparable_datetime(snapshot.captured_at) or datetime.min, snapshot.id), default=None)


def _investment_account_summaries(
    accounts: list[InvestmentAccount],
    movements: list[InvestmentMovement],
    start: date,
    end: date,
) -> list[DashboardInvestmentAccount]:
    summaries: list[DashboardInvestmentAccount] = []
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())
    for account in accounts:
        monthly = [
            movement
            for movement in movements
            if movement.investment_account_id == account.id and _in_datetime_range(movement.occurred_at, start_dt, end_dt)
        ]
        invested = sum((movement.amount for movement in monthly if movement.movement_type == "investment"), Decimal("0"))
        withdrawn = sum((movement.amount for movement in monthly if movement.movement_type == "disinvestment"), Decimal("0"))
        summaries.append(
            DashboardInvestmentAccount(
                account_id=account.id,
                name=account.name,
                institution=account.institution,
                account_type=account.account_type,
                currency=account.currency,
                current_value=money_for_currency(account.current_value, account.currency),
                month_invested=money_for_currency(invested, account.currency),
                month_withdrawn=money_for_currency(withdrawn, account.currency),
                movement_count=len(monthly),
            )
        )
    return summaries


def _is_overdue(receivable: Receivable, today: date) -> bool:
    return receivable.status == "overdue" or (receivable.due_at is not None and receivable.due_at.date() < today)


def _is_upcoming(receivable: Receivable, today: date) -> bool:
    if receivable.due_at is None:
        return False
    due_on = receivable.due_at.date()
    return today <= due_on <= today + timedelta(days=7)


def _payable_is_overdue(payable: Payable, today: date) -> bool:
    return payable.status == "overdue" or (payable.due_at is not None and payable.due_at.date() < today)


def _looks_like_supermarket(transaction: Transaction) -> bool:
    text = " ".join(
        value.lower()
        for value in [transaction.merchant_name, transaction.description, transaction.category.name if transaction.category else None]
        if value
    )
    return any(name in text for name in SUPERMARKET_NAMES) or "supermercado" in text


def _detect_subscriptions(transactions: list[Transaction]) -> list[DashboardSubscription]:
    grouped: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        if transaction.status in EXCLUDED_STATUSES or transaction.transaction_type not in {"expense", "subscription"}:
            continue
        merchant = transaction.merchant_name or ""
        if merchant:
            grouped[merchant.lower()].append(transaction)

    subscriptions: list[DashboardSubscription] = []
    for merchant_key, items in grouped.items():
        if len(items) < 2:
            continue
        ordered = sorted(items, key=lambda item: item.occurred_at)
        amounts = [_transaction_clp_amount(item) for item in ordered]
        if any(amount <= Decimal("0") for amount in amounts):
            continue
        if max(amounts) - min(amounts) > max(Decimal("2000"), max(amounts) * Decimal("0.15")):
            continue
        intervals = [
            (ordered[index].occurred_at.date() - ordered[index - 1].occurred_at.date()).days
            for index in range(1, len(ordered))
        ]
        average_interval = sum(intervals) / len(intervals) if intervals else None
        if average_interval is not None and not 25 <= average_interval <= 35:
            continue
        subscriptions.append(
            DashboardSubscription(
                merchant_name=ordered[-1].merchant_name or merchant_key,
                average_amount=money(sum(amounts, Decimal("0")) / len(amounts)),
                count=len(items),
                average_interval_days=average_interval,
            )
        )

    return sorted(subscriptions, key=lambda item: item.average_amount, reverse=True)[:8]
