export type BackendHealth = {
  status: string;
  service: string;
  environment: string;
  version: string;
};

export type Category = {
  id: number;
  parent_id: number | null;
  name: string;
  color: string;
  icon: string;
  kind: "expense" | "income" | "both";
  is_system: boolean;
  sort_order: number;
};

export type TransactionStatus =
  | "classified"
  | "needs_review"
  | "ignored"
  | "duplicate"
  | "pending_payment"
  | "partially_paid"
  | "paid"
  | "overdue";

export type TransactionType =
  | "expense"
  | "income"
  | "transfer_out"
  | "transfer_in"
  | "internal_transfer"
  | "loan_out"
  | "receivable_payment"
  | "payable_payment"
  | "investment"
  | "disinvestment"
  | "subscription"
  | "refund"
  | "unknown";

export type CashflowDirection = "inflow" | "outflow" | "neutral";

export type TransactionRelationshipCategory = "ninguna" | "amigos" | "trabajo" | "mi" | "novia";
export type CurrencyCode = "CLP" | "USD";

export type Person = {
  id: number;
  name: string;
  alias: string | null;
  email: string | null;
  phone: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type TransactionSplit = {
  id: number;
  transaction_id: number;
  category_id: number | null;
  amount: string;
  currency: CurrencyCode;
  label: string | null;
  quantity: string | null;
  notes: string | null;
  category: Category | null;
};

export type ImportCandidateSplit = {
  category_id: number | null;
  category_name: string | null;
  amount: string;
  currency: CurrencyCode;
  label: string | null;
  notes: string | null;
};

export type ImportCandidate = {
  email_message_id: number;
  import_run_id: number;
  subject: string;
  body_preview: string | null;
  body_text: string | null;
  body_html: string | null;
  received_at: string;
  sender_name: string | null;
  sender_email: string | null;
  amount: string;
  currency: CurrencyCode;
  original_amount: string | null;
  original_currency: CurrencyCode | null;
  amount_clp: string | null;
  exchange_rate: string | null;
  exchange_rate_source: string | null;
  exchange_rate_date: string | null;
  currency_detection_confidence: number | null;
  currency_detection_reason: string | null;
  merchant_name: string | null;
  counterparty: string | null;
  description: string | null;
  suggested_category_id: number | null;
  suggested_category_name: string | null;
  suggested_category_color: string | null;
  suggested_transaction_type: TransactionType;
  cashflow_direction: CashflowDirection;
  suggested_financial_account_id: number | null;
  suggested_financial_account_name: string | null;
  detected_account_institution: string | null;
  detected_account_type: string | null;
  detected_account_last_four: string | null;
  account_detection_confidence: number | null;
  account_detection_reason: string | null;
  status: TransactionStatus;
  confidence: number | null;
  classification_reason: string | null;
  classification_method: string | null;
  needs_split: boolean;
  suggested_splits: ImportCandidateSplit[];
  suggested_investment_account_id: number | null;
  suggested_investment_account_name: string | null;
};

export type ClassificationRule = {
  id: number;
  name: string;
  field:
    | "source_text"
    | "sender_email"
    | "sender_name"
    | "subject"
    | "body_preview"
    | "merchant_name"
    | "counterparty"
    | "description"
    | "detected_account_institution"
    | "detected_account_type"
    | "detected_account_last_four"
    | "item_text";
  operator: "contains" | "equals" | "starts_with" | "regex";
  pattern: string;
  category_id: number | null;
  category_name: string | null;
  transaction_type: TransactionType | null;
  financial_account_id: number | null;
  financial_account_name: string | null;
  investment_account_id: number | null;
  investment_account_name: string | null;
  priority: number;
  confidence: number;
  is_active: boolean;
  created_from_correction: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type RuleTestResponse = {
  input_preview: string;
  category_id: number | null;
  category_name: string | null;
  transaction_type: TransactionType | null;
  financial_account_id: number | null;
  financial_account_name: string | null;
  investment_account_id: number | null;
  investment_account_name: string | null;
  confidence: number | null;
  reason: string | null;
  matched_rules: Array<{
    rule_id: number;
    rule_name: string;
    field: string;
    operator: string;
    pattern: string;
    confidence: number;
    reason: string;
  }>;
};

export type RuleSuggestion = {
  field: ClassificationRule["field"];
  pattern: string;
  count: number;
  category_id: number | null;
  category_name: string | null;
  financial_account_id: number | null;
  financial_account_name: string | null;
  investment_account_id: number | null;
  investment_account_name: string | null;
  transaction_type: TransactionType | null;
  confidence: number;
  reason: string;
};

export type GmailStatus = {
  connected: boolean;
  client_configured: boolean;
  credentials_path: string;
  token_path: string;
  redirect_uri: string;
  scopes: string[];
  default_query: string;
  last_sync_at: string | null;
  last_history_id: string | null;
};

export type GmailSyncResponse = {
  import_run_id: number;
  candidates: ImportCandidate[];
  ignored_count: number;
  duplicate_count: number;
  parse_error_count: number;
  reprocessed_count: number;
  messages_seen: number;
  history_id: string | null;
};

export type GmailMessage = {
  id: number;
  gmail_message_id: string | null;
  received_at: string;
  sender_name: string | null;
  sender_email: string | null;
  subject: string;
  body_preview: string | null;
  body_text: string | null;
  body_html: string | null;
  parse_status: "parsed" | "discarded" | "parse_failed" | "confirmed" | string;
  is_visible: boolean;
  import_run_id: number | null;
};

export type ApiTransaction = {
  id: number;
  occurred_at: string;
  posted_at: string | null;
  amount: string;
  signed_amount: string | null;
  currency: CurrencyCode;
  original_amount: string | null;
  original_currency: CurrencyCode | null;
  amount_clp: string | null;
  exchange_rate: string | null;
  exchange_rate_source: string | null;
  exchange_rate_date: string | null;
  currency_detection_confidence: number | null;
  currency_detection_reason: string | null;
  merchant_name: string | null;
  counterparty: string | null;
  relationship_category: TransactionRelationshipCategory;
  financial_account_id: number | null;
  destination_account_id: number | null;
  destination_amount: string | null;
  destination_currency: CurrencyCode | null;
  investment_account_id: number | null;
  person_id: number | null;
  receivable_id: number | null;
  payable_id: number | null;
  description: string | null;
  subject: string | null;
  category_id: number | null;
  category: Category | null;
  financial_account: Pick<FinancialAccount, "id" | "name" | "institution" | "account_type" | "last_four" | "currency" | "card_art_variant" | "visual_group"> | null;
  destination_account: Pick<FinancialAccount, "id" | "name" | "institution" | "account_type" | "last_four" | "currency" | "card_art_variant" | "visual_group"> | null;
  investment_account: Pick<InvestmentAccount, "id" | "name" | "institution" | "account_type"> | null;
  person: Pick<Person, "id" | "name" | "alias"> | null;
  receivable: { id: number; title: string; remaining_amount: string; status: string } | null;
  payable: { id: number; title: string; remaining_amount: string; status: string } | null;
  source: "manual" | "gmail" | "csv" | "demo";
  source_message_id: string | null;
  payment_method: string | null;
  transaction_type: TransactionType;
  status: TransactionStatus;
  confidence: number | null;
  classification_method: string | null;
  classification_reason: string | null;
  account_detection_method: string | null;
  account_detection_confidence: number | null;
  account_detection_reason: string | null;
  notes: string | null;
  splits: TransactionSplit[];
  created_at: string;
  updated_at: string;
};

export type ReceivablePayment = {
  id: number;
  receivable_id: number;
  transaction_id: number | null;
  paid_at: string;
  amount: string;
  notes: string | null;
  created_at: string;
};

export type PayablePayment = {
  id: number;
  payable_id: number;
  transaction_id: number | null;
  paid_at: string;
  amount: string;
  notes: string | null;
  created_at: string;
};

export type Receivable = {
  id: number;
  person_id: number;
  person: Person;
  title: string;
  original_amount: string;
  remaining_amount: string;
  currency: CurrencyCode;
  issued_at: string;
  due_at: string | null;
  status: "pending_payment" | "partially_paid" | "paid" | "overdue" | "forgiven";
  notes: string | null;
  payments: ReceivablePayment[];
  created_at: string;
  updated_at: string;
};

export type Payable = {
  id: number;
  person_id: number;
  person: Person;
  title: string;
  original_amount: string;
  remaining_amount: string;
  currency: CurrencyCode;
  issued_at: string;
  due_at: string | null;
  status: "pending_payment" | "partially_paid" | "paid" | "overdue" | "forgiven";
  notes: string | null;
  payments: PayablePayment[];
  created_at: string;
  updated_at: string;
};

export type ObligationOffset = {
  id: number;
  person_id: number;
  receivable_id: number | null;
  payable_id: number | null;
  offset_at: string;
  amount: string;
  resulting_direction: "receivable" | "payable" | "settled";
  resulting_amount: string;
  notes: string | null;
  created_at: string;
};

export type FinancialAccount = {
  id: number;
  name: string;
  institution: string | null;
  account_type: "checking" | "savings" | "debit_card" | "credit_card" | "cash" | "wallet" | "unknown";
  product_name: string | null;
  last_four: string | null;
  currency: CurrencyCode;
  opening_balance: string;
  credit_limit_amount: string | null;
  credit_limit_currency: CurrencyCode | null;
  available_credit_amount: string | null;
  used_credit_amount: string | null;
  billing_cycle_day: number | null;
  payment_due_day: number | null;
  statement_amount: string | null;
  statement_currency: CurrencyCode | null;
  statement_amount_overridden: boolean;
  statement_override_reason: string | null;
  card_art_variant: "white" | "red" | "green" | "black" | "blue" | string | null;
  visual_group: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type FinancialAccountSnapshot = {
  id: number;
  financial_account_id: number;
  captured_at: string;
  balance: string;
  currency: CurrencyCode;
  source: string;
  notes: string | null;
  created_at: string;
};

export type InvestmentAccount = {
  id: number;
  name: string;
  institution: string | null;
  account_type: "brokerage" | "mutual_fund" | "pension" | "crypto" | "savings" | "other";
  currency: CurrencyCode;
  current_value: string;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type InvestmentMovement = {
  id: number;
  investment_account_id: number;
  transaction_id: number | null;
  occurred_at: string;
  movement_type: "investment" | "disinvestment" | "valuation";
  amount: string;
  currency: CurrencyCode;
  units: string | null;
  unit_price: string | null;
  source: string;
  notes: string | null;
  created_at: string;
};

export type DashboardMetrics = {
  liquid_balance: string;
  investment_balance: string;
  month_expense: string;
  month_income: string;
  net_balance: string;
  today_expense: string;
  daily_average_expense: string;
  projected_month_expense: string;
  review_count: number;
  pending_receivables: string;
  overdue_receivables: number;
  upcoming_receivables: number;
};

export type DashboardDailyPoint = {
  date: string;
  label: string;
  expense: string;
  income: string;
  balance: string;
};

export type DashboardDailyHeatmapPoint = {
  date: string;
  day: number;
  weekday: number;
  expense: string;
  intensity: number;
};

export type DashboardCategoryTotal = {
  category_id: number | null;
  name: string;
  color: string;
  amount: string;
};

export type DashboardMerchantTotal = {
  name: string;
  amount: string;
  count: number;
};

export type DashboardTransaction = {
  id: number;
  occurred_at: string;
  amount: string;
  currency: CurrencyCode;
  original_amount: string | null;
  original_currency: CurrencyCode | null;
  amount_clp: string | null;
  exchange_rate: string | null;
  currency_detection_confidence: number | null;
  currency_detection_reason: string | null;
  merchant_name: string | null;
  counterparty: string | null;
  description: string | null;
  category_name: string | null;
  category_color: string | null;
  transaction_type: TransactionType;
  status: TransactionStatus;
  has_splits: boolean;
};

export type DashboardReceivable = {
  id: number;
  person_name: string;
  title: string;
  remaining_amount: string;
  currency: CurrencyCode;
  due_at: string | null;
  status: string;
};

export type DashboardSubscription = {
  merchant_name: string;
  average_amount: string;
  count: number;
  average_interval_days: number | null;
};

export type DashboardPeriodComparison = {
  previous_label: string;
  previous_expense: string;
  expense_delta: string;
  expense_delta_percent: string | null;
  previous_income: string;
  income_delta: string;
  income_delta_percent: string | null;
  previous_net_balance: string;
  net_balance_delta: string;
};

export type DashboardInsight = {
  kind: string;
  title: string;
  detail: string;
  amount: string | null;
  severity: "info" | "success" | "warning" | string;
};

export type DashboardPersonTotal = {
  person_id: number | null;
  person_name: string;
  amount: string;
  count: number;
};

export type DashboardObligationPersonTotal = DashboardPersonTotal & {
  overdue_count: number;
  next_due_at: string | null;
};

export type DashboardBudgetProgress = {
  category_id: number | null;
  name: string;
  color: string;
  budget_amount: string;
  spent_amount: string;
  remaining_amount: string;
  usage_percent: string;
  status: "ok" | "watch" | "over" | string;
};

export type DashboardFinancialAccount = {
  account_id: number;
  name: string;
  institution: string | null;
  account_type: string;
  last_four: string | null;
  currency: CurrencyCode;
  balance: string;
  month_delta: string;
  transaction_count: number;
  credit_limit_amount: string | null;
  credit_limit_currency: CurrencyCode | null;
  used_credit_amount: string | null;
  available_credit_amount: string | null;
  billing_cycle_day: number | null;
  payment_due_day: number | null;
  statement_amount: string | null;
  statement_currency: CurrencyCode | null;
  statement_amount_overridden: boolean;
  card_art_variant: "white" | "red" | "green" | "black" | "blue" | string | null;
  visual_group: string | null;
};

export type DashboardInvestmentAccount = {
  account_id: number;
  name: string;
  institution: string | null;
  account_type: string;
  currency: CurrencyCode;
  current_value: string;
  month_invested: string;
  month_withdrawn: string;
  movement_count: number;
};

export type DashboardOverview = {
  generated_at: string;
  period: {
    from_date: string;
    to_date: string;
    label: string;
  };
  metrics: DashboardMetrics;
  daily: DashboardDailyPoint[];
  daily_heatmap: DashboardDailyHeatmapPoint[];
  period_comparison: DashboardPeriodComparison | null;
  insights: DashboardInsight[];
  expense_categories: DashboardCategoryTotal[];
  income_categories: DashboardCategoryTotal[];
  merchants: DashboardMerchantTotal[];
  budget_progress: DashboardBudgetProgress[];
  class_income_by_person: DashboardPersonTotal[];
  receivables_by_person: DashboardObligationPersonTotal[];
  payables_by_person: DashboardObligationPersonTotal[];
  mixed_purchase_totals: DashboardCategoryTotal[];
  recent_transactions: DashboardTransaction[];
  review_transactions: DashboardTransaction[];
  unallocated_supermarkets: DashboardTransaction[];
  pending_receivables: DashboardReceivable[];
  subscriptions: DashboardSubscription[];
  financial_accounts: DashboardFinancialAccount[];
  investment_accounts: DashboardInvestmentAccount[];
  unassigned_account_transactions: DashboardTransaction[];
};

export type Transaction = {
  id: number;
  occurredAt: string;
  merchant: string;
  description: string;
  amount: number;
  currency: CurrencyCode;
  category: string;
  categoryColor: string;
  source: "manual" | "gmail" | "csv" | "demo";
  status: TransactionStatus;
  confidence: number;
};

export type DailySpend = {
  day: string;
  amount: number;
};

export type CategorySpend = {
  name: string;
  amount: number;
  color: string;
};
