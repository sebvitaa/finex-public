from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DashboardPeriod(BaseModel):
    from_date: date
    to_date: date
    label: str


class DashboardMetrics(BaseModel):
    liquid_balance: Decimal = Decimal("0")
    investment_balance: Decimal = Decimal("0")
    month_expense: Decimal = Decimal("0")
    month_income: Decimal = Decimal("0")
    net_balance: Decimal = Decimal("0")
    today_expense: Decimal = Decimal("0")
    daily_average_expense: Decimal = Decimal("0")
    projected_month_expense: Decimal = Decimal("0")
    review_count: int = 0
    pending_receivables: Decimal = Decimal("0")
    overdue_receivables: int = 0
    upcoming_receivables: int = 0


class DashboardDailyPoint(BaseModel):
    date: date
    label: str
    expense: Decimal = Decimal("0")
    income: Decimal = Decimal("0")
    balance: Decimal = Decimal("0")


class DashboardDailyHeatmapPoint(BaseModel):
    date: date
    day: int
    weekday: int
    expense: Decimal = Decimal("0")
    intensity: float = 0


class DashboardCategoryTotal(BaseModel):
    category_id: int | None = None
    name: str
    color: str = "#71717A"
    amount: Decimal = Decimal("0")


class DashboardMerchantTotal(BaseModel):
    name: str
    amount: Decimal = Decimal("0")
    count: int = 0


class DashboardTransaction(BaseModel):
    id: int
    occurred_at: datetime
    amount: Decimal
    currency: str
    original_amount: Decimal | None = None
    original_currency: str | None = None
    amount_clp: Decimal | None = None
    exchange_rate: Decimal | None = None
    currency_detection_confidence: float | None = None
    currency_detection_reason: str | None = None
    merchant_name: str | None = None
    counterparty: str | None = None
    description: str | None = None
    category_name: str | None = None
    category_color: str | None = None
    transaction_type: str
    status: str
    has_splits: bool = False

    model_config = ConfigDict(from_attributes=True)


class DashboardReceivable(BaseModel):
    id: int
    person_name: str
    title: str
    remaining_amount: Decimal
    currency: str
    due_at: datetime | None = None
    status: str


class DashboardSubscription(BaseModel):
    merchant_name: str
    average_amount: Decimal
    count: int
    average_interval_days: float | None = None


class DashboardPeriodComparison(BaseModel):
    previous_label: str
    previous_expense: Decimal = Decimal("0")
    expense_delta: Decimal = Decimal("0")
    expense_delta_percent: Decimal | None = None
    previous_income: Decimal = Decimal("0")
    income_delta: Decimal = Decimal("0")
    income_delta_percent: Decimal | None = None
    previous_net_balance: Decimal = Decimal("0")
    net_balance_delta: Decimal = Decimal("0")


class DashboardInsight(BaseModel):
    kind: str
    title: str
    detail: str
    amount: Decimal | None = None
    severity: str = "info"


class DashboardPersonTotal(BaseModel):
    person_id: int | None = None
    person_name: str
    amount: Decimal = Decimal("0")
    count: int = 0


class DashboardObligationPersonTotal(DashboardPersonTotal):
    overdue_count: int = 0
    next_due_at: datetime | None = None


class DashboardBudgetProgress(BaseModel):
    category_id: int | None = None
    name: str
    color: str = "#71717A"
    budget_amount: Decimal = Decimal("0")
    spent_amount: Decimal = Decimal("0")
    remaining_amount: Decimal = Decimal("0")
    usage_percent: Decimal = Decimal("0")
    status: str = "ok"


class DashboardFinancialAccount(BaseModel):
    account_id: int
    name: str
    institution: str | None = None
    account_type: str
    last_four: str | None = None
    currency: str
    balance: Decimal = Decimal("0")
    month_delta: Decimal = Decimal("0")
    transaction_count: int = 0
    credit_limit_amount: Decimal | None = None
    credit_limit_currency: str | None = None
    used_credit_amount: Decimal | None = None
    available_credit_amount: Decimal | None = None
    billing_cycle_day: int | None = None
    payment_due_day: int | None = None
    statement_amount: Decimal | None = None
    statement_currency: str | None = None
    statement_amount_overridden: bool = False
    card_art_variant: str | None = None
    visual_group: str | None = None


class DashboardInvestmentAccount(BaseModel):
    account_id: int
    name: str
    institution: str | None = None
    account_type: str
    currency: str
    current_value: Decimal = Decimal("0")
    month_invested: Decimal = Decimal("0")
    month_withdrawn: Decimal = Decimal("0")
    movement_count: int = 0


class DashboardOverview(BaseModel):
    generated_at: datetime
    period: DashboardPeriod
    metrics: DashboardMetrics
    daily: list[DashboardDailyPoint] = Field(default_factory=list)
    daily_heatmap: list[DashboardDailyHeatmapPoint] = Field(default_factory=list)
    period_comparison: DashboardPeriodComparison | None = None
    insights: list[DashboardInsight] = Field(default_factory=list)
    expense_categories: list[DashboardCategoryTotal] = Field(default_factory=list)
    income_categories: list[DashboardCategoryTotal] = Field(default_factory=list)
    merchants: list[DashboardMerchantTotal] = Field(default_factory=list)
    budget_progress: list[DashboardBudgetProgress] = Field(default_factory=list)
    class_income_by_person: list[DashboardPersonTotal] = Field(default_factory=list)
    receivables_by_person: list[DashboardObligationPersonTotal] = Field(default_factory=list)
    payables_by_person: list[DashboardObligationPersonTotal] = Field(default_factory=list)
    mixed_purchase_totals: list[DashboardCategoryTotal] = Field(default_factory=list)
    recent_transactions: list[DashboardTransaction] = Field(default_factory=list)
    review_transactions: list[DashboardTransaction] = Field(default_factory=list)
    unallocated_supermarkets: list[DashboardTransaction] = Field(default_factory=list)
    pending_receivables: list[DashboardReceivable] = Field(default_factory=list)
    subscriptions: list[DashboardSubscription] = Field(default_factory=list)
    financial_accounts: list[DashboardFinancialAccount] = Field(default_factory=list)
    investment_accounts: list[DashboardInvestmentAccount] = Field(default_factory=list)
    unassigned_account_transactions: list[DashboardTransaction] = Field(default_factory=list)
