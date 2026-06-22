import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const dashboardResponse = {
  generated_at: "2026-05-29T12:00:00Z",
  period: { from_date: "2026-05-01", to_date: "2026-05-31", label: "05/2026" },
  metrics: {
    liquid_balance: "185000",
    investment_balance: "50000",
    month_expense: "42000",
    month_income: "25000",
    net_balance: "-17000",
    today_expense: "0",
    daily_average_expense: "1448",
    projected_month_expense: "44897",
    review_count: 0,
    pending_receivables: "30000",
    overdue_receivables: 0,
    upcoming_receivables: 1
  },
  daily: [{ date: "2026-05-10", label: "10 may", expense: "42000", income: "0", balance: "-42000" }],
  daily_heatmap: [{ date: "2026-05-10", day: 10, weekday: 7, expense: "42000", intensity: 1 }],
  period_comparison: {
    previous_label: "04/2026",
    previous_expense: "10000",
    expense_delta: "32000",
    expense_delta_percent: "320.00",
    previous_income: "0",
    income_delta: "25000",
    income_delta_percent: null,
    previous_net_balance: "-10000",
    net_balance_delta: "-7000"
  },
  insights: [{ kind: "daily_spike", title: "Dia de gasto alto", detail: "10 may supera el promedio.", amount: "42000", severity: "warning" }],
  expense_categories: [{ category_id: 1, name: "Comida", color: "#22C55E", amount: "21000" }],
  income_categories: [{ category_id: 2, name: "Clases", color: "#60A5FA", amount: "25000" }],
  merchants: [{ name: "Lider", amount: "42000", count: 1 }],
  budget_progress: [
    {
      category_id: 1,
      name: "Comida",
      color: "#22C55E",
      budget_amount: "180000",
      spent_amount: "21000",
      remaining_amount: "159000",
      usage_percent: "11.67",
      status: "ok"
    }
  ],
  class_income_by_person: [{ person_id: 1, person_name: "Alumno demo", amount: "25000", count: 1 }],
  receivables_by_person: [{ person_id: 1, person_name: "Alumno demo", amount: "30000", count: 1, overdue_count: 0, next_due_at: null }],
  payables_by_person: [],
  mixed_purchase_totals: [{ category_id: 1, name: "Comida", color: "#22C55E", amount: "21000" }],
  recent_transactions: [],
  review_transactions: [],
  unallocated_supermarkets: [],
  pending_receivables: [],
  subscriptions: [],
  financial_accounts: [],
  investment_accounts: [],
  unassigned_account_transactions: []
};

const transactionsResponse = [
  {
    id: 101,
    occurred_at: "2026-06-04T12:00:00Z",
    posted_at: null,
    amount: "12990",
    signed_amount: "-12990",
    currency: "CLP",
    merchant_name: "Movimiento activo",
    counterparty: null,
    relationship_category: "mi",
    financial_account_id: null,
    investment_account_id: null,
    person_id: null,
    receivable_id: null,
    payable_id: null,
    description: "Compra normal",
    subject: null,
    category_id: 1,
    category: { id: 1, parent_id: null, name: "Comida", color: "#22C55E", icon: "utensils", kind: "expense", is_system: true, sort_order: 10 },
    financial_account: null,
    investment_account: null,
    person: null,
    receivable: null,
    payable: null,
    source: "manual",
    source_message_id: null,
    payment_method: null,
    transaction_type: "expense",
    status: "classified",
    confidence: null,
    classification_method: null,
    classification_reason: null,
    account_detection_method: null,
    account_detection_confidence: null,
    account_detection_reason: null,
    notes: null,
    splits: [],
    created_at: "2026-06-04T12:00:00Z",
    updated_at: "2026-06-04T12:00:00Z"
  },
  {
    id: 102,
    occurred_at: "2026-06-03T12:00:00Z",
    posted_at: null,
    amount: "5000",
    signed_amount: "-5000",
    currency: "CLP",
    merchant_name: "Movimiento archivado",
    counterparty: null,
    relationship_category: "mi",
    financial_account_id: null,
    investment_account_id: null,
    person_id: null,
    receivable_id: null,
    payable_id: null,
    description: "Compra oculta",
    subject: null,
    category_id: 1,
    category: { id: 1, parent_id: null, name: "Comida", color: "#22C55E", icon: "utensils", kind: "expense", is_system: true, sort_order: 10 },
    financial_account: null,
    investment_account: null,
    person: null,
    receivable: null,
    payable: null,
    source: "manual",
    source_message_id: null,
    payment_method: null,
    transaction_type: "expense",
    status: "ignored",
    confidence: null,
    classification_method: null,
    classification_reason: null,
    account_detection_method: null,
    account_detection_confidence: null,
    account_detection_reason: null,
    notes: null,
    splits: [],
    created_at: "2026-06-03T12:00:00Z",
    updated_at: "2026-06-03T12:00:00Z"
  }
];

const peopleResponse = [
  {
    id: 1,
    name: "Alumno demo",
    alias: null,
    email: null,
    phone: null,
    notes: null,
    created_at: "2026-06-01T12:00:00Z",
    updated_at: "2026-06-01T12:00:00Z"
  }
];

const receivablesResponse = [
  {
    id: 201,
    person_id: 1,
    person: peopleResponse[0],
    title: "Clase pendiente",
    original_amount: "35000",
    remaining_amount: "30000",
    currency: "CLP",
    issued_at: "2026-06-01T12:00:00Z",
    due_at: "2026-06-10T12:00:00Z",
    status: "partially_paid",
    notes: "Queda una clase por cobrar.",
    payments: [
      {
        id: 301,
        receivable_id: 201,
        transaction_id: null,
        paid_at: "2026-06-02T12:00:00Z",
        amount: "5000",
        notes: "Abono inicial",
        created_at: "2026-06-02T12:00:00Z"
      }
    ],
    created_at: "2026-06-01T12:00:00Z",
    updated_at: "2026-06-02T12:00:00Z"
  }
];

const payablesResponse = [
  {
    id: 202,
    person_id: 1,
    person: peopleResponse[0],
    title: "Compra compartida",
    original_amount: "20000",
    remaining_amount: "15000",
    currency: "CLP",
    issued_at: "2026-06-01T13:00:00Z",
    due_at: "2026-06-12T12:00:00Z",
    status: "partially_paid",
    notes: "Parte de una compra que debo devolver.",
    payments: [
      {
        id: 302,
        payable_id: 202,
        transaction_id: null,
        paid_at: "2026-06-03T12:00:00Z",
        amount: "5000",
        notes: "Pago inicial",
        created_at: "2026-06-03T12:00:00Z"
      }
    ],
    created_at: "2026-06-01T13:00:00Z",
    updated_at: "2026-06-03T12:00:00Z"
  }
];

function mockApi() {
  global.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/health")) {
      return Response.json({ status: "ok", service: "finex", environment: "test", version: "0.1.0" });
    }
    if (url.includes("/api/v1/dashboard/overview")) {
      return Response.json(dashboardResponse);
    }
    if (url.includes("/api/v1/categories")) {
      return Response.json([
        { id: 1, parent_id: null, name: "Comida", color: "#22C55E", icon: "utensils", kind: "expense", is_system: true, sort_order: 10 },
        { id: 2, parent_id: null, name: "Clases", color: "#60A5FA", icon: "book-open", kind: "income", is_system: true, sort_order: 20 },
        { id: 3, parent_id: null, name: "Supermercado", color: "#A78BFA", icon: "shopping-basket", kind: "expense", is_system: true, sort_order: 30 },
        { id: 4, parent_id: null, name: "Cuentas por cobrar", color: "#F59E0B", icon: "hand-coins", kind: "both", is_system: true, sort_order: 40 },
        { id: 5, parent_id: null, name: "Cuentas por pagar", color: "#FB7185", icon: "receipt-text", kind: "both", is_system: true, sort_order: 41 },
        { id: 6, parent_id: null, name: "Inversiones", color: "#38BDF8", icon: "trending-up", kind: "both", is_system: true, sort_order: 42 },
        { id: 7, parent_id: null, name: "Desinversiones", color: "#A78BFA", icon: "trending-down", kind: "both", is_system: true, sort_order: 43 }
      ]);
    }
    if (url.includes("/api/v1/import/demo")) {
      return Response.json([
        {
          email_message_id: 9,
          import_run_id: 2,
          subject: "Compra aprobada Farmacia por $8.500",
          body_preview: "Comercio: Farmacia Monto: $8.500",
          received_at: "2026-05-28T12:00:00Z",
          sender_name: "Banco Demo",
          sender_email: "avisos@banco.demo",
          amount: "8500.00",
          currency: "CLP",
          merchant_name: "Farmacia",
          counterparty: null,
          description: "Compra aprobada Farmacia por $8.500",
          suggested_category_id: 1,
          suggested_category_name: "Comida",
          suggested_category_color: "#22C55E",
          suggested_transaction_type: "expense",
          cashflow_direction: "outflow",
          suggested_financial_account_id: null,
          suggested_financial_account_name: null,
          detected_account_institution: null,
          detected_account_type: null,
          detected_account_last_four: null,
          account_detection_confidence: null,
          account_detection_reason: null,
          status: "needs_review",
          confidence: 0.8,
          classification_reason: "Compra detectada",
          classification_method: "rule_engine",
          needs_split: false,
          suggested_splits: [],
          suggested_investment_account_id: null,
          suggested_investment_account_name: null
        },
        {
          email_message_id: 10,
          import_run_id: 2,
          subject: "Compra aprobada Lider por $42.000",
          body_preview: "Comercio: Lider Monto: $42.000",
          received_at: "2026-05-29T12:00:00Z",
          sender_name: "Banco Demo",
          sender_email: "avisos@banco.demo",
          amount: "42000.00",
          currency: "CLP",
          merchant_name: "Lider",
          counterparty: null,
          description: "Compra aprobada Lider por $42.000",
          suggested_category_id: 3,
          suggested_category_name: "Supermercado",
          suggested_category_color: "#A78BFA",
          suggested_transaction_type: "expense",
          cashflow_direction: "outflow",
          suggested_financial_account_id: null,
          suggested_financial_account_name: null,
          detected_account_institution: null,
          detected_account_type: null,
          detected_account_last_four: null,
          account_detection_confidence: null,
          account_detection_reason: null,
          status: "needs_review",
          confidence: 0.8,
          classification_reason: "Supermercado sin detalle suficiente",
          classification_method: "rule_engine",
          needs_split: true,
          suggested_splits: [],
          suggested_investment_account_id: null,
          suggested_investment_account_name: null
        }
      ]);
    }
    if (url.includes("/api/v1/gmail/status")) {
      return Response.json({
        connected: false,
        client_configured: true,
        credentials_path: "data/local/gmail_credentials.json",
        token_path: "data/local/gmail_token.json",
        redirect_uri: "http://127.0.0.1:8000/api/v1/gmail/callback",
        scopes: ["https://www.googleapis.com/auth/gmail.readonly"],
        default_query: "newer_than:30d",
        last_sync_at: null,
        last_history_id: null
      });
    }
    if (url.includes("/api/v1/gmail/messages")) {
      return Response.json([]);
    }
    if (url.includes("/api/v1/gmail/candidates")) {
      return Response.json([]);
    }
    if (url.includes("/api/v1/transactions")) {
      return Response.json(transactionsResponse);
    }
    if (url.includes("/api/v1/people")) {
      return Response.json(peopleResponse);
    }
    if (url.includes("/api/v1/receivables")) {
      return Response.json(receivablesResponse);
    }
    if (url.includes("/api/v1/payables")) {
      return Response.json(payablesResponse);
    }
    if (
      url.includes("/api/v1/rules") ||
      url.includes("/api/v1/financial-accounts") ||
      url.includes("/api/v1/investment-accounts")
    ) {
      return Response.json([]);
    }
    return Response.json({});
  }) as typeof fetch;
}

describe("App", () => {
  beforeEach(() => {
    mockApi();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the dashboard as the first screen", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /dashboard financiero/i })).toBeInTheDocument();
    expect(screen.getByText(/gasto del mes/i)).toBeInTheDocument();
    expect(screen.getByText(/liquidez/i)).toBeInTheDocument();
    expect(screen.getByText(/ultimos movimientos reales/i)).toBeInTheDocument();
  });

  it("opens the manual registration workspace", async () => {
    const user = userEvent.setup();

    render(<App />);
    await user.click(screen.getByRole("button", { name: /movimientos/i }));

    expect(await screen.findByRole("heading", { name: /movimientos/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /plantilla lider/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: /tabla de transacciones/i })).toBeInTheDocument();

    await user.click(screen.getByText(/detalles opcionales/i));

    expect(screen.getByText(/impacto en cuentas por cobrar\/pagar/i)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /disminuir cuenta por cobrar/i })).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/tipo/i), "transfer_in");

    expect(screen.getByText(/qué es esta transferencia/i)).toBeInTheDocument();
    expect(screen.getAllByRole("option", { name: /pago de cuenta por cobrar/i }).length).toBeGreaterThan(0);
  });

  it("keeps archived transactions reviewable without mixing them into the default view", async () => {
    const user = userEvent.setup();

    render(<App />);
    await user.click(screen.getByRole("button", { name: /movimientos/i }));

    expect(await screen.findByText(/movimiento activo/i)).toBeInTheDocument();
    expect(screen.queryByText(/movimiento archivado/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /editar movimiento movimiento activo/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /ver detalle movimiento movimiento activo/i }));

    const detailDialog = await screen.findByRole("dialog");
    expect(within(detailDialog).getByRole("heading", { name: /detalle movimiento movimiento activo/i })).toBeInTheDocument();
    expect(within(detailDialog).getByText(/cuenta o tarjeta/i)).toBeInTheDocument();

    await user.click(within(detailDialog).getByRole("button", { name: /editar movimiento/i }));

    expect(await screen.findByRole("heading", { name: /editar movimiento/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /cancelar/i }));

    await user.selectOptions(screen.getByLabelText(/vista/i), "archived");

    expect(await screen.findByText(/movimiento archivado/i)).toBeInTheDocument();
    expect(screen.queryByText(/movimiento activo/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /restaurar/i })).toBeInTheDocument();
  });

  it("opens obligations without burying them under the transaction table", async () => {
    const user = userEvent.setup();

    render(<App />);
    await user.click(screen.getByRole("button", { name: /obligaciones/i }));

    expect(await screen.findByRole("heading", { name: /obligaciones/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: /cuenta por cobrar/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: /cuenta por pagar/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: /tabla de transacciones/i })).not.toBeInTheDocument();
  });

  it("shows obligation balances and opens details only on demand", async () => {
    const user = userEvent.setup();

    render(<App />);
    await user.click(screen.getByRole("button", { name: /obligaciones/i }));

    expect(await screen.findByText(/balance neto/i)).toBeInTheDocument();
    expect(screen.getByText(/a favor mio despues de pagos/i)).toBeInTheDocument();
    expect(screen.getAllByText(/clase pendiente/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/compra compartida/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/abono inicial/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /detalle cuenta por cobrar clase pendiente/i }));

    expect(await screen.findByRole("heading", { name: /detalle cuenta por cobrar/i })).toBeInTheDocument();
    expect(screen.getByText(/pagos registrados/i)).toBeInTheDocument();
    expect(screen.getByText(/abono inicial/i)).toBeInTheDocument();
  });

  it("opens the controlled import workspace and loads demo candidates", async () => {
    const user = userEvent.setup();

    render(<App />);
    await user.click(screen.getByRole("button", { name: /importar/i }));

    expect(await screen.findByRole("heading", { name: /importar correos/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /pegar correo/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /previsualizar texto/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /conectar gmail/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /cargar demo/i }));

    const newest = await screen.findByRole("heading", { name: /compra aprobada lider/i });
    const older = await screen.findByRole("heading", { name: /compra aprobada farmacia/i });
    expect(newest.compareDocumentPosition(older) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText(/por distribuir/i)).toBeInTheDocument();
  });

  it("opens the email review workspace", async () => {
    const user = userEvent.setup();

    render(<App />);
    await user.click(screen.getByRole("button", { name: /correos/i }));

    expect(await screen.findByRole("heading", { name: /revisar correos/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /pegar correo/i })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /candidatos por revisar/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /correos existentes/i })).toBeInTheDocument();
  });

  it("opens configuration with structural administration", async () => {
    const user = userEvent.setup();

    render(<App />);
    await user.click(screen.getByRole("button", { name: /configuracion/i }));

    expect(await screen.findByRole("heading", { name: /configuracion/i })).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: /buscar ajustes/i })).toHaveAttribute("placeholder", "Buscar ajuste...");
    expect(screen.getByRole("heading", { name: /personas/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /categorias/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /correos archivados/i })).toBeInTheDocument();
  });
});
