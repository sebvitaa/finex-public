import type {
  ApiTransaction,
  BackendHealth,
  Category,
  ClassificationRule,
  DashboardOverview,
  FinancialAccount,
  FinancialAccountSnapshot,
  GmailMessage,
  GmailStatus,
  GmailSyncResponse,
  ImportCandidate,
  InvestmentAccount,
  InvestmentMovement,
  ObligationOffset,
  Payable,
  PayablePayment,
  Person,
  Receivable,
  ReceivablePayment,
  RuleSuggestion,
  RuleTestResponse,
  TransactionSplit,
  TransactionType
} from "../types";

const API_BASE_URL = import.meta.env.VITE_FINEX_API_URL ?? "";

let _activeSession: string = (() => {
  try {
    return localStorage.getItem("finex_session") ?? "personal";
  } catch {
    return "personal";
  }
})();

export function setApiSession(session: string): void {
  _activeSession = session;
}

function sessionHeaders(): Record<string, string> {
  return { "X-Finex-Session": _activeSession };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...sessionHeaders(),
      ...init?.headers
    },
    ...init
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { ...sessionHeaders(), ...init?.headers },
    ...init
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.blob();
}

function withParams(path: string, params: Record<string, string | number | boolean | undefined | null>) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  const query = searchParams.toString();
  return query ? `${path}?${query}` : path;
}

function jsonInit(method: string, body?: unknown): RequestInit {
  return {
    method,
    body: body === undefined ? undefined : JSON.stringify(body)
  };
}

export const api = {
  health: () => request<BackendHealth>("/health"),
  dashboardOverview: (params: { year?: number | ""; month?: number | "" } = {}) =>
    request<DashboardOverview>(withParams("/api/v1/dashboard/overview", params)),
  dashboardExportCsv: (params: { year?: number | ""; month?: number | "" } = {}) =>
    requestBlob(withParams("/api/v1/dashboard/export.csv", params)),
  categories: (params: { kind?: Category["kind"] } = {}) => request<Category[]>(withParams("/api/v1/categories", params)),
  createCategory: (payload: Partial<Category> & Pick<Category, "name">) =>
    request<Category>("/api/v1/categories", jsonInit("POST", payload)),
  updateCategory: (id: number, payload: Partial<Category>) => request<Category>(`/api/v1/categories/${id}`, jsonInit("PATCH", payload)),
  deleteCategory: (id: number) => request<void>(`/api/v1/categories/${id}`, jsonInit("DELETE")),
  rules: (params: { active_only?: boolean } = {}) => request<ClassificationRule[]>(withParams("/api/v1/rules", params)),
  createRule: (payload: Record<string, unknown>) => request<ClassificationRule>("/api/v1/rules", jsonInit("POST", payload)),
  updateRule: (id: number, payload: Record<string, unknown>) => request<ClassificationRule>(`/api/v1/rules/${id}`, jsonInit("PATCH", payload)),
  deleteRule: (id: number) => request<void>(`/api/v1/rules/${id}`, jsonInit("DELETE")),
  testRule: (payload: Record<string, unknown>) => request<RuleTestResponse>("/api/v1/rules/test", jsonInit("POST", payload)),
  ruleSuggestions: () => request<RuleSuggestion[]>("/api/v1/rules/suggestions"),
  transactions: (params: {
    q?: string;
    status?: string;
    category_id?: number | "";
    transaction_type?: TransactionType | "";
    relationship_category?: string;
    person_id?: number | "";
  } = {}) => request<ApiTransaction[]>(withParams("/api/v1/transactions", params)),
  createTransaction: (payload: Record<string, unknown>) => request<ApiTransaction>("/api/v1/transactions", jsonInit("POST", payload)),
  updateTransaction: (id: number, payload: Record<string, unknown>) =>
    request<ApiTransaction>(`/api/v1/transactions/${id}`, jsonInit("PATCH", payload)),
  replaceTransactionSplits: (id: number, payload: Array<Partial<TransactionSplit>>) =>
    request<ApiTransaction>(`/api/v1/transactions/${id}/splits`, jsonInit("PUT", payload)),
  people: () => request<Person[]>("/api/v1/people"),
  createPerson: (payload: Pick<Person, "name"> & Partial<Person>) => request<Person>("/api/v1/people", jsonInit("POST", payload)),
  updatePerson: (id: number, payload: Partial<Person>) => request<Person>(`/api/v1/people/${id}`, jsonInit("PATCH", payload)),
  financialAccounts: (params: { active_only?: boolean } = {}) =>
    request<FinancialAccount[]>(withParams("/api/v1/financial-accounts", params)),
  createFinancialAccount: (payload: Record<string, unknown>) =>
    request<FinancialAccount>("/api/v1/financial-accounts", jsonInit("POST", payload)),
  updateFinancialAccount: (id: number, payload: Record<string, unknown>) =>
    request<FinancialAccount>(`/api/v1/financial-accounts/${id}`, jsonInit("PATCH", payload)),
  createFinancialAccountSnapshot: (id: number, payload: Record<string, unknown>) =>
    request<FinancialAccountSnapshot>(`/api/v1/financial-accounts/${id}/snapshots`, jsonInit("POST", payload)),
  investmentAccounts: (params: { active_only?: boolean } = {}) =>
    request<InvestmentAccount[]>(withParams("/api/v1/investment-accounts", params)),
  createInvestmentAccount: (payload: Record<string, unknown>) =>
    request<InvestmentAccount>("/api/v1/investment-accounts", jsonInit("POST", payload)),
  updateInvestmentAccount: (id: number, payload: Record<string, unknown>) =>
    request<InvestmentAccount>(`/api/v1/investment-accounts/${id}`, jsonInit("PATCH", payload)),
  createInvestmentMovement: (id: number, payload: Record<string, unknown>) =>
    request<InvestmentMovement>(`/api/v1/investment-accounts/${id}/movements`, jsonInit("POST", payload)),
  receivables: (params: { status?: string; person_id?: number | "" } = {}) =>
    request<Receivable[]>(withParams("/api/v1/receivables", params)),
  createReceivable: (payload: Record<string, unknown>) => request<Receivable>("/api/v1/receivables", jsonInit("POST", payload)),
  createReceivablePayment: (id: number, payload: Record<string, unknown>) =>
    request<ReceivablePayment>(`/api/v1/receivables/${id}/payments`, jsonInit("POST", payload)),
  createReceivablePayments: (payload: Record<string, unknown>) =>
    request<ReceivablePayment[]>("/api/v1/receivables/payments", jsonInit("POST", payload)),
  offsetObligations: (payload: Record<string, unknown>) =>
    request<ObligationOffset>("/api/v1/receivables/offsets", jsonInit("POST", payload)),
  payables: (params: { status?: string; person_id?: number | "" } = {}) =>
    request<Payable[]>(withParams("/api/v1/payables", params)),
  createPayable: (payload: Record<string, unknown>) => request<Payable>("/api/v1/payables", jsonInit("POST", payload)),
  createPayablePayment: (id: number, payload: Record<string, unknown>) =>
    request<PayablePayment>(`/api/v1/payables/${id}/payments`, jsonInit("POST", payload)),
  createPayablePayments: (payload: Record<string, unknown>) =>
    request<PayablePayment[]>("/api/v1/payables/payments", jsonInit("POST", payload)),
  importText: (rawText: string) => request<ImportCandidate>("/api/v1/import/text", jsonInit("POST", { raw_text: rawText })),
  importDemo: (sampleId?: string) => request<ImportCandidate[]>("/api/v1/import/demo", jsonInit("POST", sampleId ? { sample_id: sampleId } : {})),
  confirmImport: (payload: Record<string, unknown>) =>
    request<{ transaction: ApiTransaction; email_message_id: number; import_run_id: number | null }>(
      "/api/v1/import/confirm",
      jsonInit("POST", payload)
    ),
  discardImport: (payload: { email_message_id: number; import_run_id?: number }) =>
    request<{ email_message_id: number; import_run_id: number | null; status: string }>("/api/v1/import/discard", jsonInit("POST", payload)),
  gmailStatus: () => request<GmailStatus>("/api/v1/gmail/status"),
  gmailCandidates: (limit = 20) => request<ImportCandidate[]>(withParams("/api/v1/gmail/candidates", { limit })),
  gmailMessages: (limit = 20, params: { visible_only?: boolean; archived_only?: boolean } = {}) =>
    request<GmailMessage[]>(withParams("/api/v1/gmail/messages", { limit, ...params })),
  gmailSetMessageVisibility: (id: number, isVisible: boolean) =>
    request<GmailMessage>(`/api/v1/gmail/messages/${id}/visibility`, jsonInit("PATCH", { is_visible: isVisible })),
  gmailConnect: () =>
    request<{ authorization_url: string; redirect_uri: string; scopes: string[] }>("/api/v1/gmail/connect"),
  gmailSync: (payload: { max_results?: number; query?: string; label_ids?: string[]; include_spam_trash?: boolean } = {}) =>
    request<GmailSyncResponse>("/api/v1/gmail/sync", jsonInit("POST", payload)),
  gmailDisconnect: () => request<{ connected: boolean }>("/api/v1/gmail/disconnect", jsonInit("POST")),
  sessionInfo: () => request<{ session: string; label: string; is_demo: boolean }>("/api/v1/session/info"),
  resetDemoSession: () => request<{ status: string; message: string }>("/api/v1/session/demo/reset", jsonInit("POST"))
};
