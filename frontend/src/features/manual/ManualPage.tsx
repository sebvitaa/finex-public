import { Archive, Eye, Pencil, Plus, RotateCcw, Save, SplitSquareHorizontal, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Drawer } from "../../components/ui/Drawer";
import { Modal } from "../../components/ui/Modal";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { api } from "../../lib/api";
import {
  formatCurrency,
  formatCurrencyInput,
  formatDateLabel,
  formatFinancialAccountType,
  formatInvestmentAccountType,
  normalizeMoneyInput,
  parseCurrencyInput
} from "../../lib/format";
import type {
  ApiTransaction,
  Category,
  CurrencyCode,
  FinancialAccount,
  InvestmentAccount,
  Payable,
  Person,
  Receivable,
  TransactionRelationshipCategory,
  TransactionStatus,
  TransactionType
} from "../../types";

const transactionTypes: Array<{ value: TransactionType; label: string }> = [
  { value: "expense", label: "Gasto" },
  { value: "income", label: "Ingreso" },
  { value: "transfer_in", label: "Transferencia recibida" },
  { value: "transfer_out", label: "Transferencia enviada" },
  { value: "internal_transfer", label: "Traspaso entre mis cuentas" },
  { value: "loan_out", label: "Dinero prestado" },
  { value: "receivable_payment", label: "Pago de cuenta por cobrar" },
  { value: "payable_payment", label: "Pago de cuenta por pagar" },
  { value: "investment", label: "Inversion" },
  { value: "disinvestment", label: "Desinversion" },
  { value: "subscription", label: "Suscripcion" },
  { value: "refund", label: "Devolucion" },
  { value: "unknown", label: "Desconocido" }
];

const transactionTypeLabels = new Map(transactionTypes.map((type) => [type.value, type.label]));

type TransferInPurpose = "simple_income" | "receivable_payment" | "adjustment_income" | "review_later";

const transferInPurposes: Array<{ value: TransferInPurpose; label: string; description: string }> = [
  { value: "simple_income", label: "Ingreso simple", description: "Ingreso real sin deuda asociada." },
  { value: "receivable_payment", label: "Pago de cuenta por cobrar", description: "Disminuye una cuenta por cobrar pendiente." },
  { value: "adjustment_income", label: "Ingreso por ajuste", description: "Corrige una diferencia o saldo menor." },
  { value: "review_later", label: "Revisar después", description: "Guarda el movimiento como pendiente de revisar." }
];

const transferInPurposeLabels = new Map(transferInPurposes.map((purpose) => [purpose.value, purpose.label]));

const statuses: Array<{ value: TransactionStatus; label: string }> = [
  { value: "classified", label: "Clasificado" },
  { value: "needs_review", label: "Por revisar" },
  { value: "ignored", label: "Archivado" },
  { value: "pending_payment", label: "Pendiente" },
  { value: "partially_paid", label: "Pago parcial" },
  { value: "paid", label: "Pagado" }
];

const relationshipCategories: Array<{ value: TransactionRelationshipCategory; label: string }> = [
  { value: "ninguna", label: "Ninguna" },
  { value: "amigos", label: "Amigos" },
  { value: "trabajo", label: "Trabajo" },
  { value: "mi", label: "Mi" },
  { value: "novia", label: "Novia" }
];

const relationshipLabels = new Map(relationshipCategories.map((category) => [category.value, category.label]));
const currencyOptions: CurrencyCode[] = ["CLP", "USD"];

type TransactionLifecycleView = "active" | "archived" | "all";

const lifecycleViews: Array<{ value: TransactionLifecycleView; label: string }> = [
  { value: "active", label: "Activos" },
  { value: "archived", label: "Archivados" },
  { value: "all", label: "Todos" }
];

const lifecycleSummaryLabels: Record<TransactionLifecycleView, string> = {
  active: "activos",
  archived: "archivados",
  all: "segun filtros actuales"
};

type ObligationStatus = Receivable["status"];

type ObligationDetail =
  | { kind: "receivable"; obligation: Receivable }
  | { kind: "payable"; obligation: Payable };

const obligationStatusLabels: Record<ObligationStatus, string> = {
  pending_payment: "Pendiente",
  partially_paid: "Pago parcial",
  paid: "Pagado",
  overdue: "Vencido",
  forgiven: "Condonado"
};

const obligationStatusClasses: Record<ObligationStatus, string> = {
  pending_payment: "border-warning/40 bg-warning/10 text-warning",
  partially_paid: "border-info/40 bg-info/10 text-info",
  paid: "border-accent/40 bg-accent/10 text-accent",
  overdue: "border-danger/40 bg-danger/10 text-danger",
  forgiven: "border-subtle/40 bg-surface2 text-muted"
};

const emptyTransactionForm = () => ({
  transactionType: "expense" as TransactionType,
  occurredAt: new Date().toISOString().slice(0, 16),
  amount: "",
  currency: "CLP" as CurrencyCode,
  amountClp: "",
  financialAccountId: "",
  destinationAccountId: "",
  destinationAmount: "",
  investmentAccountId: "",
  merchantName: "",
  counterparty: "",
  relationshipCategory: "mi" as TransactionRelationshipCategory,
  description: "",
  categoryId: "",
  status: "classified" as TransactionStatus,
  personId: "",
  receivableId: "",
  payableId: "",
  transferPurpose: "simple_income" as TransferInPurpose
});

const emptyEditForm = () => ({
  transactionType: "expense" as TransactionType,
  occurredAt: new Date().toISOString().slice(0, 16),
  amount: "",
  currency: "CLP" as CurrencyCode,
  amountClp: "",
  financialAccountId: "",
  destinationAccountId: "",
  destinationAmount: "",
  investmentAccountId: "",
  merchantName: "",
  counterparty: "",
  relationshipCategory: "mi" as TransactionRelationshipCategory,
  description: "",
  categoryId: "",
  status: "classified" as TransactionStatus,
  personId: "",
  receivableId: "",
  payableId: "",
  notes: ""
});

type SplitDraft = {
  categoryId: string;
  amount: string;
  label: string;
};

type ObligationImpactMode = "none" | "decrease_receivable" | "increase_receivable" | "decrease_payable" | "increase_payable";

const obligationImpactOptions: Array<{ value: ObligationImpactMode; label: string }> = [
  { value: "none", label: "No cambia cuentas por cobrar/pagar" },
  { value: "decrease_receivable", label: "Disminuir cuenta por cobrar" },
  { value: "increase_receivable", label: "Aumentar cuenta por cobrar" },
  { value: "decrease_payable", label: "Disminuir cuenta por pagar" },
  { value: "increase_payable", label: "Aumentar cuenta por pagar" }
];

const emptyObligationImpact = () => ({
  mode: "none" as ObligationImpactMode,
  receivableId: "",
  payableId: "",
  personId: "",
  amount: "",
  title: ""
});

function toDateTimeLocal(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return new Date().toISOString().slice(0, 16);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function toId(value: string) {
  return value ? Number(value) : null;
}

function toMoney(value: string | number | null | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function paidAmount(originalAmount: string, remainingAmount: string) {
  return Math.max(0, toMoney(originalAmount) - toMoney(remainingAmount));
}

function categoryOptionsFor(categories: Category[], transactionType: TransactionType) {
  const expectedKind = transactionType === "income" || transactionType === "transfer_in" || transactionType === "receivable_payment" || transactionType === "refund" ? "income" : "expense";
  return categories.filter((category) => category.kind === expectedKind || category.kind === "both");
}

function usesPersonContext(transactionType: TransactionType) {
  return ["income", "transfer_in", "transfer_out", "receivable_payment", "payable_payment", "loan_out"].includes(transactionType);
}

function financialAccountLabel(account: Pick<FinancialAccount, "account_type" | "currency" | "institution" | "last_four" | "name">) {
  const details = [account.institution, formatFinancialAccountType(account.account_type), account.currency, account.last_four ? `****${account.last_four}` : null].filter(Boolean);
  return details.length > 0 ? `${account.name} · ${details.join(" · ")}` : account.name;
}

function investmentAccountLabel(account: Pick<InvestmentAccount, "account_type" | "institution" | "name">) {
  const details = [account.institution, formatInvestmentAccountType(account.account_type)].filter(Boolean);
  return details.length > 0 ? `${account.name} · ${details.join(" · ")}` : account.name;
}

const transactionTypeBadgeClasses: Record<TransactionType, string> = {
  expense: "border-danger/40 bg-danger/10 text-danger",
  income: "border-accent/40 bg-accent/10 text-accent",
  transfer_in: "border-info/40 bg-info/10 text-info",
  transfer_out: "border-warning/40 bg-warning/10 text-warning",
  internal_transfer: "border-info/40 bg-info/10 text-info",
  loan_out: "border-warning/40 bg-warning/10 text-warning",
  receivable_payment: "border-accent/40 bg-accent/10 text-accent",
  payable_payment: "border-danger/40 bg-danger/10 text-danger",
  investment: "border-info/40 bg-info/10 text-info",
  disinvestment: "border-accent/40 bg-accent/10 text-accent",
  subscription: "border-warning/40 bg-warning/10 text-warning",
  refund: "border-accent/40 bg-accent/10 text-accent",
  unknown: "border-border bg-surface text-muted"
};

const transactionAccentColors: Record<TransactionType, string> = {
  expense: "#EF4444",
  income: "#22C55E",
  transfer_in: "#38BDF8",
  transfer_out: "#F59E0B",
  internal_transfer: "#14B8A6",
  loan_out: "#F59E0B",
  receivable_payment: "#22C55E",
  payable_payment: "#EF4444",
  investment: "#38BDF8",
  disinvestment: "#A78BFA",
  subscription: "#F59E0B",
  refund: "#22C55E",
  unknown: "#71717A"
};

const positiveTransactionTypes = new Set<TransactionType>(["income", "transfer_in", "receivable_payment", "refund", "disinvestment"]);
const negativeTransactionTypes = new Set<TransactionType>(["expense", "transfer_out", "payable_payment", "subscription"]);

function transactionTitle(transaction: ApiTransaction) {
  return transaction.merchant_name ?? transaction.counterparty ?? transaction.description ?? transactionTypeLabels.get(transaction.transaction_type) ?? "Movimiento manual";
}

function transactionSubtitle(transaction: ApiTransaction) {
  return transaction.description && transaction.description !== transactionTitle(transaction)
    ? transaction.description
    : transaction.subject ?? transaction.notes ?? "Sin motivo registrado";
}

function transactionAccountLabel(transaction: ApiTransaction) {
  if (transaction.transaction_type === "internal_transfer" && transaction.financial_account && transaction.destination_account) {
    return `${transaction.financial_account.name} → ${transaction.destination_account.name}`;
  }
  if (transaction.financial_account) return financialAccountLabel(transaction.financial_account);
  if (transaction.investment_account) return investmentAccountLabel(transaction.investment_account);
  return "Sin cuenta asignada";
}

function transactionAmountTone(transactionType: TransactionType) {
  if (positiveTransactionTypes.has(transactionType)) return "text-accent";
  if (negativeTransactionTypes.has(transactionType)) return "text-danger";
  return "text-info";
}

function transactionAmountPrefix(transactionType: TransactionType) {
  if (positiveTransactionTypes.has(transactionType)) return "+";
  if (negativeTransactionTypes.has(transactionType)) return "-";
  return "";
}

function transactionAccentColor(transaction: ApiTransaction) {
  return transaction.category?.color ?? transactionAccentColors[transaction.transaction_type] ?? transactionAccentColors.unknown;
}

function supportsInternalReceivableImpact(transactionType: TransactionType) {
  return transactionType === "expense" || transactionType === "subscription";
}

function supportsInternalPayableImpact(transactionType: TransactionType) {
  return ["income", "transfer_in", "refund", "disinvestment"].includes(transactionType);
}

function balanceLabel(amount: number) {
  if (amount > 0) return "A favor mio";
  if (amount < 0) return "En contra mia";
  return "Cuadrado";
}

function balanceTone(amount: number) {
  if (amount > 0) return "text-accent";
  if (amount < 0) return "text-danger";
  return "text-muted";
}

function ObligationStatusBadge({ status }: { status: ObligationStatus }) {
  return (
    <span className={`inline-flex rounded-[8px] border px-2 py-1 text-xs ${obligationStatusClasses[status]}`}>
      {obligationStatusLabels[status]}
    </span>
  );
}

function ObligationDetailContent({ detail }: { detail: ObligationDetail }) {
  const obligation = detail.obligation;
  const remainingAmount = toMoney(obligation.remaining_amount);
  const paid = paidAmount(obligation.original_amount, obligation.remaining_amount);
  const personLine =
    detail.kind === "receivable"
      ? `${obligation.person.name} me debe este saldo.`
      : `Tengo que pagarle este saldo a ${obligation.person.name}.`;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-[8px] border border-border bg-surface2 p-3">
          <p className="text-xs uppercase text-subtle">Pendiente</p>
          <p className={`mt-1 text-lg font-semibold ${detail.kind === "receivable" ? "text-accent" : "text-danger"}`}>
            {formatCurrency(remainingAmount, obligation.currency)}
          </p>
        </div>
        <div className="rounded-[8px] border border-border bg-surface2 p-3">
          <p className="text-xs uppercase text-subtle">Original</p>
          <p className="mt-1 text-lg font-semibold text-text">{formatCurrency(toMoney(obligation.original_amount), obligation.currency)}</p>
        </div>
        <div className="rounded-[8px] border border-border bg-surface2 p-3">
          <p className="text-xs uppercase text-subtle">Pagado</p>
          <p className="mt-1 text-lg font-semibold text-muted">{formatCurrency(paid, obligation.currency)}</p>
        </div>
      </div>

      <div className="space-y-2 text-sm text-muted">
        <div className="flex items-center justify-between gap-3">
          <span>Estado</span>
          <ObligationStatusBadge status={obligation.status} />
        </div>
        <div className="flex justify-between gap-3">
          <span>Persona</span>
          <span className="text-right text-text">{obligation.person.name}</span>
        </div>
        <div className="flex justify-between gap-3">
          <span>Vencimiento</span>
          <span className="text-right text-text">{obligation.due_at ? formatDateLabel(obligation.due_at) : "Sin vencimiento"}</span>
        </div>
        <p className="rounded-[8px] border border-border bg-surface2 p-3 text-text">{personLine}</p>
        {obligation.notes ? <p className="rounded-[8px] border border-border bg-surface2 p-3">{obligation.notes}</p> : null}
      </div>

      <div>
        <h3 className="text-sm font-semibold text-text">Pagos registrados</h3>
        <div className="mt-2 space-y-2">
          {obligation.payments.map((payment) => (
            <div className="flex items-center justify-between gap-3 rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm" key={payment.id}>
              <div>
                <p className="text-text">{formatCurrency(toMoney(payment.amount), obligation.currency)}</p>
                <p className="text-xs text-subtle">{formatDateLabel(payment.paid_at)}</p>
              </div>
              <p className="max-w-[220px] truncate text-right text-xs text-muted">{payment.notes ?? "Sin nota"}</p>
            </div>
          ))}
          {obligation.payments.length === 0 ? <p className="rounded-[8px] border border-border bg-surface2 px-3 py-4 text-sm text-muted">Sin pagos registrados todavia.</p> : null}
        </div>
      </div>
    </div>
  );
}

function TransactionDetailContent({ transaction }: { transaction: ApiTransaction }) {
  const accentColor = transactionAccentColor(transaction);
  const details = [
    ["Fecha", formatDateLabel(transaction.occurred_at)],
    ["Tipo", transactionTypeLabels.get(transaction.transaction_type) ?? transaction.transaction_type],
    ["Moneda", transaction.currency],
    [
      "Equivalente CLP",
      transaction.amount_clp ? formatCurrency(Number(transaction.amount_clp), "CLP") : transaction.currency === "CLP" ? formatCurrency(Number(transaction.amount), "CLP") : "Pendiente"
    ],
    ["Categoria", transaction.category?.name ?? "Sin categoria"],
    ["Estado", statuses.find((status) => status.value === transaction.status)?.label ?? transaction.status],
    ["Relacion", relationshipLabels.get(transaction.relationship_category) ?? "Ninguna"],
    ["Persona", transaction.person?.name ?? "Sin persona"],
    ["Cuenta o tarjeta", transactionAccountLabel(transaction)],
    ["Origen", transaction.source ?? "manual"]
  ];

  return (
    <div className="space-y-4">
      <div className="rounded-[8px] border border-border bg-surface2 p-4" style={{ borderColor: `${accentColor}66` }}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <span className={`inline-flex rounded-[8px] border px-2 py-1 text-xs font-medium ${transactionTypeBadgeClasses[transaction.transaction_type]}`}>
              {transactionTypeLabels.get(transaction.transaction_type) ?? transaction.transaction_type}
            </span>
            <h3 className="mt-3 truncate text-xl font-semibold text-text">{transactionTitle(transaction)}</h3>
            <p className="mt-1 text-sm text-muted">{transactionSubtitle(transaction)}</p>
          </div>
          <div className="shrink-0 rounded-[8px] border border-border bg-surface px-3 py-2 text-right">
            <p className="text-xs text-subtle">Monto</p>
            <p className={`mt-1 text-lg font-semibold ${transactionAmountTone(transaction.transaction_type)}`}>
              {transactionAmountPrefix(transaction.transaction_type)}
              {formatCurrency(Number(transaction.amount), transaction.currency)}
            </p>
            {transaction.currency !== "CLP" ? (
              <p className="mt-1 text-xs text-subtle">
                {transaction.amount_clp ? `Eq. ${formatCurrency(Number(transaction.amount_clp), "CLP")}` : "Sin equivalente CLP"}
              </p>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {details.map(([label, value]) => (
          <div className="rounded-[8px] border border-border bg-surface2 px-3 py-2" key={label}>
            <p className="text-xs uppercase tracking-wide text-subtle">{label}</p>
            <p className="mt-1 text-sm text-text">{value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-[8px] border border-border bg-surface2 p-3">
          <p className="text-xs uppercase tracking-wide text-subtle">Comercio o lugar</p>
          <p className="mt-1 text-sm text-text">{transaction.merchant_name ?? "No registrado"}</p>
        </div>
        <div className="rounded-[8px] border border-border bg-surface2 p-3">
          <p className="text-xs uppercase tracking-wide text-subtle">Persona, origen o destino</p>
          <p className="mt-1 text-sm text-text">{transaction.counterparty ?? "No registrado"}</p>
        </div>
      </div>

      {transaction.notes ? (
        <div className="rounded-[8px] border border-border bg-surface2 p-3">
          <p className="text-xs uppercase tracking-wide text-subtle">Nota interna</p>
          <p className="mt-1 text-sm text-muted">{transaction.notes}</p>
        </div>
      ) : null}

      {transaction.currency_detection_reason ? (
        <div className="rounded-[8px] border border-info/30 bg-info/10 p-3">
          <p className="text-xs uppercase tracking-wide text-info">Deteccion de moneda</p>
          <p className="mt-1 text-sm text-text">{transaction.currency_detection_reason}</p>
        </div>
      ) : null}

      <div className="rounded-[8px] border border-border bg-surface2 p-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-text">Desglose por categorias</h3>
          <span className="text-xs text-subtle">{transaction.splits.length} partes</span>
        </div>
        <div className="mt-2 space-y-2">
          {transaction.splits.map((split) => (
            <div className="flex items-center justify-between gap-3 rounded-[8px] border border-border bg-surface px-3 py-2 text-sm" key={split.id}>
              <div className="min-w-0">
                <p className="truncate text-text">{split.category?.name ?? "Sin categoria"}</p>
                <p className="truncate text-xs text-subtle">{split.label ?? "Sin etiqueta"}</p>
              </div>
              <p className="font-semibold text-text">{formatCurrency(Number(split.amount), split.currency)}</p>
            </div>
          ))}
          {transaction.splits.length === 0 ? <p className="rounded-[8px] border border-border bg-surface px-3 py-4 text-sm text-muted">Sin desglose registrado.</p> : null}
        </div>
      </div>
    </div>
  );
}

type ManualPageMode = "movements" | "obligations";

type ManualPageProps = {
  mode?: ManualPageMode;
};

export function ManualPage({ mode = "movements" }: ManualPageProps) {
  const showMovements = mode === "movements";
  const showObligations = mode === "obligations";
  const [categories, setCategories] = useState<Category[]>([]);
  const [financialAccounts, setFinancialAccounts] = useState<FinancialAccount[]>([]);
  const [investmentAccounts, setInvestmentAccounts] = useState<InvestmentAccount[]>([]);
  const [transactions, setTransactions] = useState<ApiTransaction[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [receivables, setReceivables] = useState<Receivable[]>([]);
  const [payables, setPayables] = useState<Payable[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState({
    q: "",
    transactionType: "" as TransactionType | "",
    categoryId: "",
    status: "",
    relationshipCategory: "" as TransactionRelationshipCategory | "",
    personId: "",
    lifecycleView: "active" as TransactionLifecycleView
  });

  const [transactionForm, setTransactionForm] = useState(emptyTransactionForm);
  const [splitDrafts, setSplitDrafts] = useState<SplitDraft[]>([]);
  const [obligationImpact, setObligationImpact] = useState(emptyObligationImpact);
  const [quickCategoryName, setQuickCategoryName] = useState("");
  const [receivableForm, setReceivableForm] = useState({ personId: "", title: "", amount: "", dueAt: "", notes: "" });
  const [payableForm, setPayableForm] = useState({ personId: "", title: "", amount: "", dueAt: "", notes: "" });
  const [receivablePaymentFilter, setReceivablePaymentFilter] = useState({ personId: "", q: "", transactionId: "" });
  const [payablePaymentFilter, setPayablePaymentFilter] = useState({ personId: "", q: "", transactionId: "" });
  const [offsetForm, setOffsetForm] = useState({ personId: "", receivableId: "", payableId: "", amount: "" });
  const [paymentDrafts, setPaymentDrafts] = useState<Record<number, string>>({});
  const [payablePaymentDrafts, setPayablePaymentDrafts] = useState<Record<number, string>>({});
  const [editing, setEditing] = useState<ApiTransaction | null>(null);
  const [selectedTransaction, setSelectedTransaction] = useState<ApiTransaction | null>(null);
  const [selectedObligation, setSelectedObligation] = useState<ObligationDetail | null>(null);
  const [editForm, setEditForm] = useState(emptyEditForm);
  const [editSplitDrafts, setEditSplitDrafts] = useState<SplitDraft[]>([]);

  const loadReferenceData = useCallback(async () => {
    const [categoryData, financialAccountData, investmentAccountData, peopleData, receivableData, payableData] = await Promise.all([
      api.categories(),
      api.financialAccounts(),
      api.investmentAccounts(),
      api.people(),
      api.receivables(),
      api.payables()
    ]);
    setCategories(categoryData);
    setFinancialAccounts(financialAccountData);
    setInvestmentAccounts(investmentAccountData);
    setPeople(peopleData);
    setReceivables(receivableData);
    setPayables(payableData);
  }, []);

  const loadTransactions = useCallback(async () => {
    const data = await api.transactions({
      q: filters.q,
      status: filters.status,
      category_id: filters.categoryId ? Number(filters.categoryId) : "",
      transaction_type: filters.transactionType,
      relationship_category: filters.relationshipCategory || undefined,
      person_id: filters.personId ? Number(filters.personId) : ""
    });
    setTransactions(data);
  }, [filters]);

  useEffect(() => {
    let ignore = false;
    setIsLoading(true);
    Promise.all([loadReferenceData(), loadTransactions()])
      .then(() => {
        if (!ignore) setError(null);
      })
      .catch(() => {
        if (!ignore) setError("No pude cargar los datos manuales. Revisa que el backend este arriba.");
      })
      .finally(() => {
        if (!ignore) setIsLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, [loadReferenceData, loadTransactions]);

  const visibleCategories = useMemo(
    () => categoryOptionsFor(categories, transactionForm.transactionType),
    [categories, transactionForm.transactionType]
  );
  const visibleEditCategories = useMemo(
    () => categoryOptionsFor(categories, editForm.transactionType),
    [categories, editForm.transactionType]
  );
  const compatibleFinancialAccounts = useMemo(
    () => financialAccounts.filter((account) => account.currency === transactionForm.currency),
    [financialAccounts, transactionForm.currency]
  );
  const compatibleEditFinancialAccounts = useMemo(
    () => financialAccounts.filter((account) => account.currency === editForm.currency),
    [editForm.currency, financialAccounts]
  );
  const visibleTransactions = useMemo(() => {
    if (filters.lifecycleView === "archived") {
      return transactions.filter((transaction) => transaction.status === "ignored");
    }
    if (filters.lifecycleView === "all") {
      return transactions;
    }
    return transactions.filter((transaction) => transaction.status !== "ignored");
  }, [filters.lifecycleView, transactions]);
  const pendingReceivables = useMemo(() => receivables.filter((receivable) => toMoney(receivable.remaining_amount) > 0), [receivables]);
  const pendingPayables = useMemo(() => payables.filter((payable) => toMoney(payable.remaining_amount) > 0), [payables]);
  const pendingReceivableTotal = useMemo(
    () => pendingReceivables.reduce((total, receivable) => total + toMoney(receivable.remaining_amount), 0),
    [pendingReceivables]
  );
  const pendingPayableTotal = useMemo(
    () => pendingPayables.reduce((total, payable) => total + toMoney(payable.remaining_amount), 0),
    [pendingPayables]
  );
  const obligationNetTotal = pendingReceivableTotal - pendingPayableTotal;
  const personObligationBalances = useMemo(() => {
    const balances = new Map<number, { personName: string; receivable: number; payable: number }>();
    pendingReceivables.forEach((receivable) => {
      const current = balances.get(receivable.person_id) ?? { personName: receivable.person.name, receivable: 0, payable: 0 };
      current.receivable += toMoney(receivable.remaining_amount);
      balances.set(receivable.person_id, current);
    });
    pendingPayables.forEach((payable) => {
      const current = balances.get(payable.person_id) ?? { personName: payable.person.name, receivable: 0, payable: 0 };
      current.payable += toMoney(payable.remaining_amount);
      balances.set(payable.person_id, current);
    });
    return Array.from(balances.entries())
      .map(([personId, balance]) => ({ personId, ...balance, net: balance.receivable - balance.payable }))
      .sort((left, right) => Math.abs(right.net) - Math.abs(left.net));
  }, [pendingPayables, pendingReceivables]);

  const filteredReceivables = useMemo(() => {
    const query = receivablePaymentFilter.q.trim().toLowerCase();
    return receivables.filter((receivable) => {
      if (Number(receivable.remaining_amount) <= 0) return false;
      if (receivablePaymentFilter.personId && receivable.person_id !== Number(receivablePaymentFilter.personId)) return false;
      if (!query) return true;
      return `${receivable.person.name} ${receivable.title} ${receivable.notes ?? ""}`.toLowerCase().includes(query);
    });
  }, [receivablePaymentFilter.personId, receivablePaymentFilter.q, receivables]);

  const filteredPayables = useMemo(() => {
    const query = payablePaymentFilter.q.trim().toLowerCase();
    return payables.filter((payable) => {
      if (Number(payable.remaining_amount) <= 0) return false;
      if (payablePaymentFilter.personId && payable.person_id !== Number(payablePaymentFilter.personId)) return false;
      if (!query) return true;
      return `${payable.person.name} ${payable.title} ${payable.notes ?? ""}`.toLowerCase().includes(query);
    });
  }, [payablePaymentFilter.personId, payablePaymentFilter.q, payables]);

  const linkableTransactions = useMemo(
    () => transactions.filter((transaction) => ["income", "transfer_in", "receivable_payment"].includes(transaction.transaction_type)),
    [transactions]
  );

  const outgoingLinkableTransactions = useMemo(
    () => transactions.filter((transaction) => ["transfer_out", "payable_payment"].includes(transaction.transaction_type)),
    [transactions]
  );

  const offsetReceivables = useMemo(
    () => receivables.filter((receivable) => Number(receivable.remaining_amount) > 0 && (!offsetForm.personId || receivable.person_id === Number(offsetForm.personId))),
    [offsetForm.personId, receivables]
  );

  const offsetPayables = useMemo(
    () => payables.filter((payable) => Number(payable.remaining_amount) > 0 && (!offsetForm.personId || payable.person_id === Number(offsetForm.personId))),
    [offsetForm.personId, payables]
  );

  const findCategory = useCallback(
    (name: string) => categories.find((category) => category.name.toLowerCase() === name.toLowerCase()),
    [categories]
  );

  async function refreshAfterMutation(message: string) {
    await Promise.all([loadReferenceData(), loadTransactions()]);
    setFeedback(message);
    setError(null);
  }

  async function createQuickCategory() {
    if (!quickCategoryName.trim()) return;
    const created = await api.createCategory({
      name: quickCategoryName.trim(),
      color: transactionForm.transactionType === "income" ? "#60A5FA" : "#F472B6",
      icon: "tag",
      kind: transactionForm.transactionType === "income" ? "income" : "expense",
      sort_order: 250
    });
    setQuickCategoryName("");
    setTransactionForm((current) => ({ ...current, categoryId: String(created.id) }));
    await loadReferenceData();
  }

  function applyLiderTemplate() {
    const supermercado = findCategory("Supermercado");
    const golosinas = findCategory("Golosinas");
    const comida = findCategory("Comida");
    const aseo = findCategory("Aseo y limpieza");
    setTransactionForm((current) => ({
      ...current,
      transactionType: "expense",
      merchantName: "Lider",
      amount: "42000",
      categoryId: supermercado ? String(supermercado.id) : current.categoryId,
      description: "Compra mixta supermercado"
    }));
    setSplitDrafts([
      { categoryId: golosinas ? String(golosinas.id) : "", amount: "8000", label: "Golosinas" },
      { categoryId: comida ? String(comida.id) : "", amount: "21000", label: "Comida" },
      { categoryId: aseo ? String(aseo.id) : "", amount: "10000", label: "Aseo y limpieza" },
      { categoryId: supermercado ? String(supermercado.id) : "", amount: "3000", label: "Otros" }
    ]);
  }

  async function createTransaction() {
    const transactionAmount = Number(transactionForm.amount);
    if (!Number.isFinite(transactionAmount) || transactionAmount <= 0) {
      setError("Ingresa un monto mayor a cero.");
      return;
    }

    const isInternalTransfer = transactionForm.transactionType === "internal_transfer";
    if (isInternalTransfer) {
      if (!transactionForm.financialAccountId) {
        setError("Elige la cuenta de origen del traspaso.");
        return;
      }
      if (!transactionForm.destinationAccountId) {
        setError("Elige la cuenta de destino del traspaso.");
        return;
      }
      if (transactionForm.financialAccountId === transactionForm.destinationAccountId) {
        setError("La cuenta de destino debe ser distinta a la de origen.");
        return;
      }
      const destinationAccount = financialAccounts.find((account) => account.id === Number(transactionForm.destinationAccountId));
      if (destinationAccount && destinationAccount.currency !== transactionForm.currency && !transactionForm.destinationAmount) {
        setError(`Indica el monto recibido en ${destinationAccount.currency} para el traspaso entre monedas distintas.`);
        return;
      }
    }

    const selectedReceivable = pendingReceivables.find((receivable) => receivable.id === Number(obligationImpact.receivableId));
    const selectedPayable = pendingPayables.find((payable) => payable.id === Number(obligationImpact.payableId));
    const rawImpactAmount = obligationImpact.amount.trim() || transactionForm.amount;
    const impactAmount = Number(rawImpactAmount);
    const impactPersonId = obligationImpact.personId || transactionForm.personId;
    const transferPurpose = transactionForm.transactionType === "transfer_in" ? transactionForm.transferPurpose : null;
    const transferPurposeLabel = transferPurpose ? transferInPurposeLabels.get(transferPurpose) : null;
    const adjustmentCategory = transferPurpose === "adjustment_income" ? findCategory("Ingreso por ajuste") : null;
    const impactTitle =
      obligationImpact.title.trim() ||
      transactionForm.description.trim() ||
      transactionForm.counterparty.trim() ||
      transactionForm.merchantName.trim() ||
      "Movimiento compartido";

    if (obligationImpact.mode === "decrease_receivable" && !selectedReceivable) {
      setError("Elige la cuenta por cobrar que quieres disminuir.");
      return;
    }
    if (obligationImpact.mode === "decrease_payable" && !selectedPayable) {
      setError("Elige la cuenta por pagar que quieres disminuir.");
      return;
    }
    if ((obligationImpact.mode === "increase_receivable" || obligationImpact.mode === "increase_payable") && !impactPersonId) {
      setError("Elige la persona asociada a la cuenta por cobrar/pagar.");
      return;
    }
    if (obligationImpact.mode !== "none" && (!Number.isFinite(impactAmount) || impactAmount <= 0)) {
      setError("Ingresa un monto valido para el impacto en obligaciones.");
      return;
    }

    const usesInternalReceivable =
      obligationImpact.mode === "increase_receivable" &&
      supportsInternalReceivableImpact(transactionForm.transactionType) &&
      impactAmount < transactionAmount;
    const usesInternalPayable =
      obligationImpact.mode === "increase_payable" &&
      supportsInternalPayableImpact(transactionForm.transactionType) &&
      impactAmount < transactionAmount;

    const occurredAt = new Date(transactionForm.occurredAt).toISOString();
    const splits = splitDrafts
      .filter((split) => split.amount && Number(split.amount) > 0)
      .map((split) => ({
        category_id: toId(split.categoryId),
        amount: split.amount,
        currency: transactionForm.currency,
        label: split.label || null
      }));
    const inferredPersonId = toId(transactionForm.personId) ?? selectedReceivable?.person_id ?? selectedPayable?.person_id ?? null;

    let created: ApiTransaction;
    try {
      created = await api.createTransaction({
        occurred_at: occurredAt,
        amount: transactionForm.amount,
        currency: transactionForm.currency,
        original_amount: transactionForm.amount,
        original_currency: transactionForm.currency,
        amount_clp: transactionForm.currency === "CLP" ? transactionForm.amount : transactionForm.amountClp || null,
        exchange_rate:
          transactionForm.currency === "USD" && transactionForm.amountClp
            ? String(Number(transactionForm.amountClp) / Number(transactionForm.amount))
            : null,
        currency_detection_confidence: 1,
        currency_detection_reason: "Moneda elegida manualmente",
        merchant_name: transactionForm.merchantName || null,
        counterparty: transactionForm.counterparty || null,
        relationship_category: transactionForm.relationshipCategory,
        description: transactionForm.description || transferPurposeLabel || null,
        category_id: toId(transactionForm.categoryId) ?? adjustmentCategory?.id ?? null,
        financial_account_id: toId(transactionForm.financialAccountId),
        destination_account_id: isInternalTransfer ? toId(transactionForm.destinationAccountId) : null,
        destination_amount: isInternalTransfer && transactionForm.destinationAmount ? transactionForm.destinationAmount : null,
        investment_account_id: toId(transactionForm.investmentAccountId),
        person_id: inferredPersonId,
        receivable_id: selectedReceivable ? selectedReceivable.id : null,
        payable_id: selectedPayable ? selectedPayable.id : null,
        source: "manual",
        transaction_type: transactionForm.transactionType,
        status: transferPurpose === "review_later" ? "needs_review" : transactionForm.status,
        classification_method: "manual",
        splits,
        internal_receivables: usesInternalReceivable
          ? [
              {
                person_id: Number(impactPersonId),
                title: impactTitle,
                amount: rawImpactAmount,
                notes: "Cuenta por cobrar creada desde movimiento manual"
              }
            ]
          : [],
        internal_payables: usesInternalPayable
          ? [
              {
                person_id: Number(impactPersonId),
                title: impactTitle,
                amount: rawImpactAmount,
                notes: "Cuenta por pagar creada desde movimiento manual"
              }
            ]
          : []
      });
    } catch {
      setError("No pude crear el movimiento. Si tiene desglose, la suma debe coincidir con el monto propio.");
      return;
    }

    try {
      if (selectedReceivable) {
        const amount = Math.min(impactAmount, Number(selectedReceivable.remaining_amount));
        if (amount > 0) {
          await api.createReceivablePayment(selectedReceivable.id, {
            transaction_id: created.id,
            paid_at: occurredAt,
            amount: String(amount),
            notes: "Pago registrado desde movimiento manual"
          });
        }
      }
      if (selectedPayable) {
        const amount = Math.min(impactAmount, Number(selectedPayable.remaining_amount));
        if (amount > 0) {
          await api.createPayablePayment(selectedPayable.id, {
            transaction_id: created.id,
            paid_at: occurredAt,
            amount: String(amount),
            notes: "Pago registrado desde movimiento manual"
          });
        }
      }
      if (obligationImpact.mode === "increase_receivable" && !usesInternalReceivable) {
        await api.createReceivable({
          person_id: Number(impactPersonId),
          title: impactTitle,
          original_amount: rawImpactAmount,
          currency: transactionForm.currency,
          issued_at: occurredAt,
          due_at: null,
          notes: "Cuenta por cobrar creada desde movimiento manual"
        });
      }
      if (obligationImpact.mode === "increase_payable" && !usesInternalPayable) {
        await api.createPayable({
          person_id: Number(impactPersonId),
          title: impactTitle,
          original_amount: rawImpactAmount,
          currency: transactionForm.currency,
          issued_at: occurredAt,
          due_at: null,
          notes: "Cuenta por pagar creada desde movimiento manual"
        });
      }
      setTransactionForm(emptyTransactionForm());
      setSplitDrafts([]);
      setObligationImpact(emptyObligationImpact());
      await refreshAfterMutation("Movimiento creado y obligaciones actualizadas.");
    } catch {
      await Promise.all([loadReferenceData(), loadTransactions()]);
      setError("El movimiento se guardo, pero no pude aplicar el impacto en cuentas por cobrar/pagar.");
    }
  }

  async function updateTransaction(id: number, payload: Record<string, unknown>) {
    try {
      await api.updateTransaction(id, payload);
      await refreshAfterMutation("Movimiento actualizado.");
      return true;
    } catch {
      setError("No pude actualizar el movimiento.");
      return false;
    }
  }

  async function createReceivable() {
    if (!receivableForm.personId || !receivableForm.amount || !receivableForm.title.trim()) return;
    await api.createReceivable({
      person_id: Number(receivableForm.personId),
      title: receivableForm.title.trim(),
      original_amount: receivableForm.amount,
      currency: "CLP",
      issued_at: new Date().toISOString(),
      due_at: receivableForm.dueAt ? new Date(receivableForm.dueAt).toISOString() : null,
      notes: receivableForm.notes || null
    });
    setReceivableForm({ personId: "", title: "", amount: "", dueAt: "", notes: "" });
    await refreshAfterMutation("Cuenta por cobrar creada.");
  }

  async function createPayable() {
    if (!payableForm.personId || !payableForm.amount || !payableForm.title.trim()) return;
    await api.createPayable({
      person_id: Number(payableForm.personId),
      title: payableForm.title.trim(),
      original_amount: payableForm.amount,
      currency: "CLP",
      issued_at: new Date().toISOString(),
      due_at: payableForm.dueAt ? new Date(payableForm.dueAt).toISOString() : null,
      notes: payableForm.notes || null
    });
    setPayableForm({ personId: "", title: "", amount: "", dueAt: "", notes: "" });
    await refreshAfterMutation("Cuenta por pagar creada.");
  }

  async function payReceivable(receivable: Receivable, amount: string) {
    if (!amount || Number(amount) <= 0) return;
    await api.createReceivablePayment(receivable.id, {
      paid_at: new Date().toISOString(),
      amount,
      notes: "Pago registrado desde UI"
    });
    setPaymentDrafts((current) => ({ ...current, [receivable.id]: "" }));
    await refreshAfterMutation("Pago registrado.");
  }

  async function payPayable(payable: Payable, amount: string) {
    if (!amount || Number(amount) <= 0) return;
    await api.createPayablePayment(payable.id, {
      paid_at: new Date().toISOString(),
      amount,
      notes: "Pago registrado desde UI"
    });
    setPayablePaymentDrafts((current) => ({ ...current, [payable.id]: "" }));
    await refreshAfterMutation("Pago de cuenta por pagar registrado.");
  }

  async function linkReceivablePayments() {
    const payments = filteredReceivables
      .map((receivable) => ({
        receivable_id: receivable.id,
        amount: paymentDrafts[receivable.id] ?? "",
        notes: "Pago enlazado desde cuentas por cobrar"
      }))
      .filter((payment) => payment.amount && Number(payment.amount) > 0);
    if (payments.length === 0) return;
    try {
      await api.createReceivablePayments({
        transaction_id: toId(receivablePaymentFilter.transactionId),
        paid_at: new Date().toISOString(),
        notes: "Pago enlazado desde cuentas por cobrar",
        payments
      });
      setPaymentDrafts((current) => {
        const next = { ...current };
        payments.forEach((payment) => {
          delete next[payment.receivable_id];
        });
        return next;
      });
      await refreshAfterMutation("Pagos enlazados a cuentas por cobrar.");
    } catch {
      setError("No pude enlazar esos pagos. Revisa que no excedan lo pendiente ni el monto de la transferencia.");
    }
  }

  async function linkPayablePayments() {
    const payments = filteredPayables
      .map((payable) => ({
        payable_id: payable.id,
        amount: payablePaymentDrafts[payable.id] ?? "",
        notes: "Pago enlazado desde cuentas por pagar"
      }))
      .filter((payment) => payment.amount && Number(payment.amount) > 0);
    if (payments.length === 0) return;
    try {
      await api.createPayablePayments({
        transaction_id: toId(payablePaymentFilter.transactionId),
        paid_at: new Date().toISOString(),
        notes: "Pago enlazado desde cuentas por pagar",
        payments
      });
      setPayablePaymentDrafts((current) => {
        const next = { ...current };
        payments.forEach((payment) => {
          delete next[payment.payable_id];
        });
        return next;
      });
      await refreshAfterMutation("Pagos enlazados a cuentas por pagar.");
    } catch {
      setError("No pude enlazar esos pagos. Revisa que no excedan lo pendiente ni el monto transferido.");
    }
  }

  async function offsetObligations() {
    if (!offsetForm.personId || !offsetForm.receivableId || !offsetForm.payableId) return;
    try {
      await api.offsetObligations({
        person_id: Number(offsetForm.personId),
        receivable_id: Number(offsetForm.receivableId),
        payable_id: Number(offsetForm.payableId),
        offset_at: new Date().toISOString(),
        amount: offsetForm.amount || null,
        notes: "Compensacion manual entre cuentas por cobrar y pagar"
      });
      setOffsetForm({ personId: "", receivableId: "", payableId: "", amount: "" });
      await refreshAfterMutation("Cuentas compensadas.");
    } catch {
      setError("No pude compensar esas cuentas. Deben ser de la misma persona y tener saldo pendiente.");
    }
  }

  function openEdit(transaction: ApiTransaction) {
    setEditing(transaction);
    setEditForm({
      transactionType: transaction.transaction_type,
      occurredAt: toDateTimeLocal(transaction.occurred_at),
      amount: normalizeMoneyInput(transaction.amount, transaction.currency),
      currency: transaction.currency,
      amountClp: normalizeMoneyInput(transaction.amount_clp ?? "", "CLP"),
      financialAccountId: transaction.financial_account_id ? String(transaction.financial_account_id) : "",
      destinationAccountId: transaction.destination_account_id ? String(transaction.destination_account_id) : "",
      destinationAmount: transaction.destination_amount ? normalizeMoneyInput(transaction.destination_amount, transaction.destination_currency ?? transaction.currency) : "",
      investmentAccountId: transaction.investment_account_id ? String(transaction.investment_account_id) : "",
      merchantName: transaction.merchant_name ?? "",
      counterparty: transaction.counterparty ?? "",
      relationshipCategory: transaction.relationship_category,
      description: transaction.description ?? "",
      categoryId: transaction.category_id ? String(transaction.category_id) : "",
      status: transaction.status,
      personId: transaction.person_id ? String(transaction.person_id) : "",
      receivableId: transaction.receivable_id ? String(transaction.receivable_id) : "",
      payableId: transaction.payable_id ? String(transaction.payable_id) : "",
      notes: transaction.notes ?? ""
    });
    setEditSplitDrafts(
      transaction.splits.map((split) => ({
        categoryId: split.category_id ? String(split.category_id) : "",
        amount: split.amount,
        label: split.label ?? ""
      }))
    );
  }

  function closeEdit() {
    setEditing(null);
    setEditForm(emptyEditForm());
    setEditSplitDrafts([]);
  }

  async function saveEdit() {
    if (!editing) return;
    const splits = editSplitDrafts
      .filter((split) => split.amount && Number(split.amount) > 0)
      .map((split) => ({
        category_id: toId(split.categoryId),
        amount: split.amount,
        currency: editForm.currency,
        label: split.label || null
      }));

    const saved = await updateTransaction(editing.id, {
      occurred_at: new Date(editForm.occurredAt).toISOString(),
      merchant_name: editForm.merchantName || null,
      counterparty: editForm.counterparty || null,
      amount: editForm.amount,
      currency: editForm.currency,
      original_amount: editForm.amount,
      original_currency: editForm.currency,
      amount_clp: editForm.currency === "CLP" ? editForm.amount : editForm.amountClp || null,
      exchange_rate: editForm.currency === "USD" && editForm.amountClp ? String(Number(editForm.amountClp) / Number(editForm.amount)) : null,
      category_id: toId(editForm.categoryId),
      financial_account_id: toId(editForm.financialAccountId),
      destination_account_id: editForm.transactionType === "internal_transfer" ? toId(editForm.destinationAccountId) : null,
      destination_amount: editForm.transactionType === "internal_transfer" && editForm.destinationAmount ? editForm.destinationAmount : null,
      investment_account_id: ["investment", "disinvestment"].includes(editForm.transactionType) ? toId(editForm.investmentAccountId) : null,
      person_id: toId(editForm.personId),
      receivable_id: editCanUseReceivable ? toId(editForm.receivableId) : null,
      payable_id: editCanUsePayable ? toId(editForm.payableId) : null,
      transaction_type: editForm.transactionType,
      relationship_category: editForm.relationshipCategory,
      description: editForm.description || null,
      status: editForm.status,
      notes: editForm.notes || null,
      splits
    });
    if (saved) closeEdit();
  }

  const formUsesPersonContext = usesPersonContext(transactionForm.transactionType);
  const formContextValue = formUsesPersonContext ? transactionForm.counterparty : transactionForm.merchantName;
  const editUsesPersonContext = usesPersonContext(editForm.transactionType);
  const editCanUseReceivable = ["transfer_in", "receivable_payment"].includes(editForm.transactionType);
  const editCanUsePayable = ["transfer_out", "payable_payment"].includes(editForm.transactionType);
  const editSelectedCategory = categories.find((category) => category.id === Number(editForm.categoryId));
  const editSelectedAccount = financialAccounts.find((account) => account.id === Number(editForm.financialAccountId));
  const editSelectedDestinationAccount = financialAccounts.find((account) => account.id === Number(editForm.destinationAccountId));
  const editSelectedInvestmentAccount = investmentAccounts.find((account) => account.id === Number(editForm.investmentAccountId));
  const editSelectedPerson = people.find((person) => person.id === Number(editForm.personId));
  const editMovementTitle = editForm.merchantName || editForm.counterparty || editing?.merchant_name || editing?.counterparty || "Movimiento manual";

  return (
    <div className="space-y-4">
      {error && <div className="panel border-danger/50 px-4 py-3 text-sm text-danger">{error}</div>}
      {feedback && <div className="panel border-accent/50 px-4 py-3 text-sm text-accent">{feedback}</div>}

      {showMovements ? (
      <section className="grid gap-4">
        <div className="panel p-4">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">Nuevo movimiento</h2>
              <p className="text-sm text-muted">Registra lo esencial primero. Los detalles quedan abajo si los necesitas.</p>
            </div>
            <button className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-text" onClick={applyLiderTemplate} type="button">
              <SplitSquareHorizontal aria-hidden="true" className="mr-2 inline h-4 w-4" />
              Plantilla Lider
            </button>
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <label className="text-sm text-muted">
              Tipo
              <select
                className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                onChange={(event) => {
                  const transactionType = event.target.value as TransactionType;
                  setTransactionForm((current) => ({
                    ...current,
                    transactionType,
                    transferPurpose: transactionType === "transfer_in" ? current.transferPurpose : "simple_income"
                  }));
                  if (transactionType !== "transfer_in") {
                    setObligationImpact((current) => (current.mode === "decrease_receivable" ? emptyObligationImpact() : current));
                  }
                }}
                value={transactionForm.transactionType}
              >
                {transactionTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm text-muted">
              Fecha
              <input
                className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                onChange={(event) => setTransactionForm((current) => ({ ...current, occurredAt: event.target.value }))}
                type="datetime-local"
                value={transactionForm.occurredAt}
              />
            </label>
            <label className="text-sm text-muted">
              Monto
              <div className="mt-1 grid grid-cols-[1fr_88px] gap-2">
                <input
                  className="focus-ring w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                  inputMode="decimal"
                  onChange={(event) =>
                    setTransactionForm((current) => ({ ...current, amount: parseCurrencyInput(event.target.value, current.currency) }))
                  }
                  placeholder={transactionForm.currency === "USD" ? "22.00" : "12990"}
                  value={formatCurrencyInput(transactionForm.amount, transactionForm.currency)}
                />
                <select
                  className="focus-ring rounded-[8px] border border-border bg-surface2 px-2 py-2 text-text"
                  onChange={(event) => {
                    const currency = event.target.value as CurrencyCode;
                    setTransactionForm((current) => ({
                      ...current,
                      currency,
                      amount: parseCurrencyInput(current.amount, currency),
                      amountClp: currency === "CLP" ? "" : current.amountClp,
                      financialAccountId: financialAccounts.some((account) => account.id === Number(current.financialAccountId) && account.currency === currency)
                        ? current.financialAccountId
                        : ""
                    }));
                  }}
                  value={transactionForm.currency}
                >
                  {currencyOptions.map((currency) => (
                    <option key={currency} value={currency}>
                      {currency}
                    </option>
                  ))}
                </select>
              </div>
              {transactionForm.currency === "USD" ? (
                <input
                  className="focus-ring mt-2 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-subtle"
                  inputMode="numeric"
                  onChange={(event) => setTransactionForm((current) => ({ ...current, amountClp: parseCurrencyInput(event.target.value, "CLP") }))}
                  placeholder="Equivalente CLP opcional"
                  value={formatCurrencyInput(transactionForm.amountClp, "CLP")}
                />
              ) : null}
            </label>
            <label className="text-sm text-muted">
              Categoria
              <select
                className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                onChange={(event) => setTransactionForm((current) => ({ ...current, categoryId: event.target.value }))}
                value={transactionForm.categoryId}
              >
                <option value="">Elegir</option>
                {visibleCategories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto]">
            {transactionForm.transactionType === "transfer_in" ? (
              <label className="text-sm text-muted">
                ¿Qué es esta transferencia?
                <select
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                  onChange={(event) => {
                    const transferPurpose = event.target.value as TransferInPurpose;
                    setTransactionForm((current) => ({
                      ...current,
                      transferPurpose,
                      status: transferPurpose === "review_later" ? "needs_review" : current.status
                    }));
                    if (transferPurpose === "receivable_payment") {
                      setObligationImpact((current) => ({ ...current, mode: "decrease_receivable" }));
                    } else {
                      setObligationImpact((current) => (current.mode === "decrease_receivable" ? emptyObligationImpact() : current));
                    }
                  }}
                  value={transactionForm.transferPurpose}
                >
                  {transferInPurposes.map((purpose) => (
                    <option key={purpose.value} value={purpose.value}>
                      {purpose.label}
                    </option>
                  ))}
                </select>
                <span className="mt-1 block text-xs text-subtle">
                  {transferInPurposes.find((purpose) => purpose.value === transactionForm.transferPurpose)?.description}
                </span>
                {transactionForm.transferPurpose === "receivable_payment" ? (
                  <select
                    className="focus-ring mt-2 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                    onChange={(event) => setObligationImpact((current) => ({ ...current, mode: "decrease_receivable", receivableId: event.target.value }))}
                    value={obligationImpact.receivableId}
                  >
                    <option value="">Cuenta por cobrar pendiente</option>
                    {pendingReceivables.map((receivable) => (
                      <option key={receivable.id} value={receivable.id}>
                        {receivable.person.name} · {receivable.title} · {formatCurrency(Number(receivable.remaining_amount), receivable.currency)}
                      </option>
                    ))}
                  </select>
                ) : null}
              </label>
            ) : (
              <input
                className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text placeholder:text-subtle"
                onChange={(event) =>
                  setTransactionForm((current) =>
                    formUsesPersonContext
                      ? { ...current, counterparty: event.target.value, merchantName: "" }
                      : { ...current, merchantName: event.target.value, counterparty: "" }
                  )
                }
                placeholder={formUsesPersonContext ? "Persona, origen o destino" : "Lugar, comercio o descripcion"}
                value={formContextValue}
              />
            )}
            <button className="focus-ring rounded-[8px] bg-accent px-4 py-2 text-sm font-semibold text-black" onClick={createTransaction} type="button">
              <Save aria-hidden="true" className="mr-2 inline h-4 w-4" />
              Guardar
            </button>
          </div>

          <details className="mt-4 rounded-[8px] border border-border bg-surface2 p-3">
            <summary className="focus-ring cursor-pointer rounded-[8px] text-sm font-semibold text-text">
              Detalles opcionales
              <span className="ml-2 text-xs font-normal text-subtle">relacion, cuentas, estado y nota</span>
            </summary>
            <div className="mt-3 grid gap-3 md:grid-cols-4">
              <select
                className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-text"
                onChange={(event) =>
                  setTransactionForm((current) => ({ ...current, relationshipCategory: event.target.value as TransactionRelationshipCategory }))
                }
                value={transactionForm.relationshipCategory}
              >
                {relationshipCategories.map((category) => (
                  <option key={category.value} value={category.value}>
                    {category.label}
                  </option>
                ))}
              </select>
              {formUsesPersonContext ? (
                <select
                  className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-text"
                  onChange={(event) => setTransactionForm((current) => ({ ...current, personId: event.target.value }))}
                  value={transactionForm.personId}
                >
                  <option value="">Persona opcional</option>
                  {people.map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.name}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-muted">Sin persona</div>
              )}
              <select
                className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-text"
                onChange={(event) => setTransactionForm((current) => ({ ...current, status: event.target.value as TransactionStatus }))}
                value={transactionForm.status}
              >
                {statuses.map((status) => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <label className="text-sm text-muted">
                {transactionForm.transactionType === "internal_transfer" ? "Cuenta de origen" : "Cuenta o tarjeta"}
                <select
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-text"
                  onChange={(event) => setTransactionForm((current) => ({ ...current, financialAccountId: event.target.value }))}
                  value={transactionForm.financialAccountId}
                >
                  <option value="">Sin cuenta</option>
                  {compatibleFinancialAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {financialAccountLabel(account)}
                    </option>
                  ))}
                </select>
              </label>
              {transactionForm.transactionType === "internal_transfer" ? (
                <label className="text-sm text-muted">
                  Cuenta de destino
                  <select
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-text"
                    onChange={(event) => setTransactionForm((current) => ({ ...current, destinationAccountId: event.target.value }))}
                    value={transactionForm.destinationAccountId}
                  >
                    <option value="">Elegir cuenta</option>
                    {financialAccounts
                      .filter((account) => String(account.id) !== transactionForm.financialAccountId)
                      .map((account) => (
                        <option key={account.id} value={account.id}>
                          {financialAccountLabel(account)}
                        </option>
                      ))}
                  </select>
                </label>
              ) : transactionForm.transactionType === "investment" || transactionForm.transactionType === "disinvestment" ? (
                <label className="text-sm text-muted">
                  Cuenta de inversion
                  <select
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-text"
                    onChange={(event) => setTransactionForm((current) => ({ ...current, investmentAccountId: event.target.value }))}
                    value={transactionForm.investmentAccountId}
                  >
                    <option value="">Sin cuenta de inversion</option>
                      {investmentAccounts.map((account) => (
                        <option key={account.id} value={account.id}>
                          {investmentAccountLabel(account)}
                        </option>
                      ))}
                  </select>
                </label>
              ) : (
                <div className="rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-muted">
                  Cuenta de inversion solo para inversion/desinversion
                </div>
              )}
            </div>

            {transactionForm.transactionType === "internal_transfer" ? (
              (() => {
                const destinationAccount = financialAccounts.find((account) => account.id === Number(transactionForm.destinationAccountId));
                const crossCurrency = Boolean(destinationAccount && destinationAccount.currency !== transactionForm.currency);
                return (
                  <div className="mt-2 rounded-[8px] border border-info/30 bg-info/5 px-3 py-2 text-xs text-muted">
                    Es un movimiento de capital entre tus cuentas: descuenta del origen y abona al destino, sin contar como ingreso ni gasto.
                    {crossCurrency ? (
                      <label className="mt-2 block text-sm text-muted">
                        Monto recibido en {destinationAccount?.currency}
                        <input
                          className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-text"
                          inputMode="decimal"
                          onChange={(event) => setTransactionForm((current) => ({ ...current, destinationAmount: event.target.value }))}
                          placeholder={`Monto en ${destinationAccount?.currency}`}
                          value={transactionForm.destinationAmount}
                        />
                      </label>
                    ) : null}
                  </div>
                );
              })()
            ) : null}

            <div className="mt-3 rounded-[8px] border border-border bg-surface px-3 py-3">
              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-text">Impacto en cuentas por cobrar/pagar</h3>
                  <p className="mt-1 text-xs text-subtle">Usalo cuando el movimiento paga una deuda o crea una deuda nueva con otra persona.</p>
                </div>
                <span className="w-fit rounded-[8px] border border-border bg-surface2 px-2 py-1 text-xs text-muted">Opcional</span>
              </div>
              <div className="mt-3 grid gap-3 lg:grid-cols-[1.1fr_1fr_140px]">
                <label className="text-sm text-muted">
                  Accion
                  <select
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                    onChange={(event) =>
                      setObligationImpact((current) => ({
                        ...emptyObligationImpact(),
                        mode: event.target.value as ObligationImpactMode,
                        amount: current.amount
                      }))
                    }
                    value={obligationImpact.mode}
                  >
                    {obligationImpactOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                {obligationImpact.mode === "decrease_receivable" ? (
                  <label className="text-sm text-muted">
                    Cuenta por cobrar
                    <select
                      className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                      onChange={(event) => setObligationImpact((current) => ({ ...current, receivableId: event.target.value }))}
                      value={obligationImpact.receivableId}
                    >
                      <option value="">Elegir pendiente</option>
                      {pendingReceivables.map((receivable) => (
                        <option key={receivable.id} value={receivable.id}>
                          {receivable.person.name} · {receivable.title} · {formatCurrency(Number(receivable.remaining_amount), receivable.currency)}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : obligationImpact.mode === "decrease_payable" ? (
                  <label className="text-sm text-muted">
                    Cuenta por pagar
                    <select
                      className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                      onChange={(event) => setObligationImpact((current) => ({ ...current, payableId: event.target.value }))}
                      value={obligationImpact.payableId}
                    >
                      <option value="">Elegir pendiente</option>
                      {pendingPayables.map((payable) => (
                        <option key={payable.id} value={payable.id}>
                          {payable.person.name} · {payable.title} · {formatCurrency(Number(payable.remaining_amount), payable.currency)}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : obligationImpact.mode === "increase_receivable" || obligationImpact.mode === "increase_payable" ? (
                  <label className="text-sm text-muted">
                    Persona
                    <select
                      className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                      onChange={(event) => setObligationImpact((current) => ({ ...current, personId: event.target.value }))}
                      value={obligationImpact.personId || transactionForm.personId}
                    >
                      <option value="">Elegir persona</option>
                      {people.map((person) => (
                        <option key={person.id} value={person.id}>
                          {person.name}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <div className="rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-muted">
                    No se tocaran saldos pendientes.
                  </div>
                )}

                <label className="text-sm text-muted">
                  Monto
                  <input
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text placeholder:text-subtle"
                    inputMode="decimal"
                    onChange={(event) => setObligationImpact((current) => ({ ...current, amount: parseCurrencyInput(event.target.value, transactionForm.currency) }))}
                    placeholder={formatCurrencyInput(transactionForm.amount, transactionForm.currency) || "Monto"}
                    value={formatCurrencyInput(obligationImpact.amount, transactionForm.currency)}
                  />
                </label>
              </div>

              {(obligationImpact.mode === "increase_receivable" || obligationImpact.mode === "increase_payable") && (
                <input
                  className="focus-ring mt-3 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text placeholder:text-subtle"
                  onChange={(event) => setObligationImpact((current) => ({ ...current, title: event.target.value }))}
                  placeholder={obligationImpact.mode === "increase_receivable" ? "Motivo de la cuenta por cobrar" : "Motivo de la cuenta por pagar"}
                  value={obligationImpact.title}
                />
              )}
            </div>

            <input
              className="focus-ring mt-3 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-text placeholder:text-subtle"
              onChange={(event) => setTransactionForm((current) => ({ ...current, description: event.target.value }))}
              placeholder="Descripcion o nota breve"
              value={transactionForm.description}
            />
          </details>

          <details className="mt-4 panel-tight p-3">
            <summary className="focus-ring cursor-pointer rounded-[8px] text-sm font-semibold text-text">
              Crear categoria rapida
              <span className="ml-2 text-xs font-normal text-subtle">solo si no existe en la lista</span>
            </summary>
            <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h3 className="text-sm font-semibold">Crear categoria sin salir del flujo</h3>
                <p className="text-xs text-subtle">Util para casos como Golosinas, Aseo o ingresos por clases.</p>
              </div>
              <div className="flex gap-2">
                <input
                  className="focus-ring min-w-0 rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-subtle"
                  onChange={(event) => setQuickCategoryName(event.target.value)}
                  placeholder="Nueva categoria"
                  value={quickCategoryName}
                />
                <button className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-text" onClick={createQuickCategory} type="button">
                  <Plus aria-hidden="true" className="h-4 w-4" />
                </button>
              </div>
            </div>
          </details>

          <details className="mt-4 rounded-[8px] border border-border bg-surface2 p-3" open={splitDrafts.length > 0}>
            <summary className="focus-ring cursor-pointer rounded-[8px] text-sm font-semibold text-text">
              Desglose por categorias
              <span className="ml-2 text-xs font-normal text-subtle">opcional para compras mixtas</span>
            </summary>
            <div className="mt-3 flex items-center justify-between">
              <p className="text-xs text-subtle">{splitDrafts.length} partes preparadas</p>
              <button
                className="focus-ring rounded-[8px] border border-border px-3 py-2 text-xs text-muted hover:text-text"
                onClick={() => setSplitDrafts((current) => [...current, { categoryId: "", amount: "", label: "" }])}
                type="button"
              >
                Agregar parte
              </button>
            </div>
            <div className="mt-2 space-y-2">
              {splitDrafts.map((split, index) => (
                <div className="grid gap-2 md:grid-cols-[1fr_120px_1fr_auto]" key={`${index}-${split.label}`}>
                  <select
                    className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                    onChange={(event) =>
                      setSplitDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, categoryId: event.target.value } : item)))
                    }
                    value={split.categoryId}
                  >
                    <option value="">Categoria</option>
                    {visibleCategories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                  <input
                    className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                    inputMode="decimal"
                    onChange={(event) =>
                      setSplitDrafts((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, amount: parseCurrencyInput(event.target.value, transactionForm.currency) } : item
                        )
                      )
                    }
                    placeholder="Monto"
                    value={formatCurrencyInput(split.amount, transactionForm.currency)}
                  />
                  <input
                    className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                    onChange={(event) =>
                      setSplitDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, label: event.target.value } : item)))
                    }
                    placeholder="Etiqueta"
                    value={split.label}
                  />
                  <button
                    className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-danger"
                    onClick={() => setSplitDrafts((current) => current.filter((_, itemIndex) => itemIndex !== index))}
                    type="button"
                  >
                    <Trash2 aria-hidden="true" className="h-4 w-4" />
                  </button>
                </div>
              ))}
              {splitDrafts.length === 0 && <p className="text-sm text-subtle">Opcional. Usalo para repartir compras mixtas de supermercado.</p>}
            </div>
          </details>
        </div>

      </section>
      ) : null}

      {showMovements ? (
      <section className="panel p-4">
        <div className="mb-4 flex flex-col gap-3 2xl:flex-row 2xl:items-end 2xl:justify-between">
          <div className="min-w-[220px]">
            <h2 className="text-base font-semibold">Tabla de transacciones</h2>
            <p className="text-sm text-muted">
              {isLoading ? "Cargando..." : `${visibleTransactions.length} movimientos ${lifecycleSummaryLabels[filters.lifecycleView]}.`}
            </p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-7">
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))} placeholder="Buscar" value={filters.q} />
            <label className="sr-only" htmlFor="transaction-lifecycle-view">Vista</label>
            <select
              className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
              id="transaction-lifecycle-view"
              onChange={(event) => setFilters((current) => ({ ...current, lifecycleView: event.target.value as TransactionLifecycleView }))}
              value={filters.lifecycleView}
            >
              {lifecycleViews.map((view) => <option key={view.value} value={view.value}>{view.label}</option>)}
            </select>
            <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFilters((current) => ({ ...current, transactionType: event.target.value as TransactionType | "" }))} value={filters.transactionType}>
              <option value="">Todos los tipos</option>
              {transactionTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
            </select>
            <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFilters((current) => ({ ...current, categoryId: event.target.value }))} value={filters.categoryId}>
              <option value="">Todas las categorias</option>
              {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
            </select>
            <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))} value={filters.status}>
              <option value="">Todos los estados</option>
              {statuses.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}
            </select>
            <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFilters((current) => ({ ...current, relationshipCategory: event.target.value as TransactionRelationshipCategory | "" }))} value={filters.relationshipCategory}>
              <option value="">Todas las relaciones</option>
              {relationshipCategories.map((category) => <option key={category.value} value={category.value}>{category.label}</option>)}
            </select>
            <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFilters((current) => ({ ...current, personId: event.target.value }))} value={filters.personId}>
              <option value="">Todas las personas</option>
              {people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}
            </select>
          </div>
        </div>
        <div className="space-y-3">
          {visibleTransactions.map((transaction) => {
            const title = transactionTitle(transaction);
            const accentColor = transactionAccentColor(transaction);
            const categoryName = transaction.category?.name ?? "Sin categoria";
            const personName = transaction.person?.name ?? transaction.counterparty ?? "Sin persona";

            return (
              <article
                className="relative overflow-hidden rounded-[8px] border border-border bg-surface2 p-4 shadow-panel"
                key={transaction.id}
                style={{ borderColor: `${accentColor}55` }}
              >
                <div className="absolute inset-y-0 left-0 w-1.5" style={{ backgroundColor: accentColor }} />
                <div className="pl-2">
                  <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`inline-flex rounded-[8px] border px-2 py-1 text-xs font-medium ${transactionTypeBadgeClasses[transaction.transaction_type]}`}>
                          {transactionTypeLabels.get(transaction.transaction_type) ?? transaction.transaction_type}
                        </span>
                        <span
                          className="inline-flex rounded-[8px] border px-2 py-1 text-xs font-medium text-text"
                          style={{ backgroundColor: `${accentColor}18`, borderColor: `${accentColor}66` }}
                        >
                          {categoryName}
                        </span>
                        <StatusBadge status={transaction.status} />
                      </div>
                      <h3 className="mt-3 truncate text-lg font-semibold text-text">{title}</h3>
                      <p className="mt-1 line-clamp-2 text-sm text-muted">{transactionSubtitle(transaction)}</p>
                    </div>

                    <div className="shrink-0 space-y-2 xl:w-72">
                      <div className="rounded-[8px] border border-border bg-surface px-3 py-2 text-left xl:text-right">
                        <p className="text-xs uppercase tracking-wide text-subtle">Monto</p>
                        <p className={`mt-1 text-xl font-semibold ${transactionAmountTone(transaction.transaction_type)}`}>
                          {transactionAmountPrefix(transaction.transaction_type)}
                          {formatCurrency(Number(transaction.amount), transaction.currency)}
                        </p>
                        {transaction.currency !== "CLP" ? (
                          <p className="mt-1 text-xs text-subtle">
                            {transaction.amount_clp ? `Eq. ${formatCurrency(Number(transaction.amount_clp), "CLP")}` : "Eq. CLP pendiente"}
                          </p>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap gap-2 xl:justify-end">
                        <button
                          aria-label={`Ver detalle movimiento ${title}`}
                          className="focus-ring inline-flex items-center gap-2 rounded-[8px] border border-info/40 bg-info/10 px-3 py-2 text-sm font-medium text-info hover:border-info"
                          onClick={() => setSelectedTransaction(transaction)}
                          type="button"
                        >
                          <Eye aria-hidden="true" className="h-4 w-4" />
                          Ver detalle
                        </button>
                        <button
                          aria-label={`Editar movimiento ${title}`}
                          className="focus-ring inline-flex items-center gap-2 rounded-[8px] border border-accent/40 bg-accent/10 px-3 py-2 text-sm font-medium text-accent hover:border-accent"
                          onClick={() => openEdit(transaction)}
                          type="button"
                        >
                          <Pencil aria-hidden="true" className="h-4 w-4" />
                          Editar
                        </button>
                        {transaction.status === "ignored" ? (
                          <button
                            aria-label={`Restaurar movimiento ${title}`}
                            className="focus-ring inline-flex items-center gap-2 rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-accent"
                            onClick={() => updateTransaction(transaction.id, { status: "classified" })}
                            type="button"
                          >
                            <RotateCcw aria-hidden="true" className="h-4 w-4" />
                            Restaurar
                          </button>
                        ) : (
                          <button
                            aria-label={`Archivar movimiento ${title}`}
                            className="focus-ring inline-flex items-center gap-2 rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-warning"
                            onClick={() => updateTransaction(transaction.id, { status: "ignored" })}
                            type="button"
                          >
                            <Archive aria-hidden="true" className="h-4 w-4" />
                            Archivar
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-[8px] border border-border bg-surface px-3 py-2">
                      <p className="text-xs uppercase tracking-wide text-subtle">Fecha</p>
                      <p className="mt-1 text-sm text-text">{formatDateLabel(transaction.occurred_at)}</p>
                    </div>
                    <div className="rounded-[8px] border border-border bg-surface px-3 py-2">
                      <p className="text-xs uppercase tracking-wide text-subtle">Cuenta</p>
                      <p className="mt-1 truncate text-sm text-text">{transactionAccountLabel(transaction)}</p>
                    </div>
                    <div className="rounded-[8px] border border-border bg-surface px-3 py-2">
                      <p className="text-xs uppercase tracking-wide text-subtle">Persona</p>
                      <p className="mt-1 truncate text-sm text-text">{personName}</p>
                    </div>
                    <div className="rounded-[8px] border border-border bg-surface px-3 py-2">
                      <p className="text-xs uppercase tracking-wide text-subtle">Relacion</p>
                      <p className="mt-1 text-sm text-text">{relationshipLabels.get(transaction.relationship_category) ?? "Ninguna"}</p>
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="block max-w-sm text-xs text-subtle">
                      Categoria rapida
                      <select
                        className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                        onChange={(event) =>
                          updateTransaction(transaction.id, {
                            category_id: toId(event.target.value),
                            status: transaction.status === "ignored" ? "ignored" : "classified"
                          })
                        }
                        value={transaction.category_id ?? ""}
                      >
                        <option value="">Sin categoria</option>
                        {categories.map((category) => (
                          <option key={category.id} value={category.id}>
                            {category.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                </div>
              </article>
            );
          })}
          {visibleTransactions.length === 0 ? (
            <p className="rounded-[8px] border border-border bg-surface2 px-4 py-6 text-sm text-muted">
              No hay movimientos con estos filtros. Cambia la vista o limpia la busqueda para revisar otros registros.
            </p>
          ) : null}
        </div>
      </section>
      ) : null}

      {showObligations ? (
      <>
      <section className="grid gap-3 lg:grid-cols-3">
        <div className="panel border-accent/40 p-4">
          <p className="text-xs uppercase text-subtle">Por cobrar</p>
          <p className="mt-1 text-2xl font-semibold text-accent">{formatCurrency(pendingReceivableTotal)}</p>
          <p className="mt-1 text-sm text-muted">{pendingReceivables.length} cuentas pendientes donde te deben plata.</p>
        </div>
        <div className="panel border-danger/40 p-4">
          <p className="text-xs uppercase text-subtle">Por pagar</p>
          <p className="mt-1 text-2xl font-semibold text-danger">{formatCurrency(pendingPayableTotal)}</p>
          <p className="mt-1 text-sm text-muted">{pendingPayables.length} cuentas pendientes que tienes que pagar.</p>
        </div>
        <div className="panel p-4">
          <p className="text-xs uppercase text-subtle">Balance neto</p>
          <p className={`mt-1 text-2xl font-semibold ${balanceTone(obligationNetTotal)}`}>{formatCurrency(Math.abs(obligationNetTotal))}</p>
          <p className="mt-1 text-sm text-muted">{balanceLabel(obligationNetTotal)} despues de pagos y compensaciones.</p>
        </div>
      </section>

      <section className="panel p-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <h2 className="text-base font-semibold">Balance por persona</h2>
            <p className="mt-1 text-sm text-muted">Mira rapidamente si cada persona queda a favor tuyo, en contra tuya o cuadrada.</p>
          </div>
          <div className="grid flex-1 gap-2 sm:grid-cols-2 xl:max-w-4xl xl:grid-cols-3">
            {personObligationBalances.map((balance) => (
              <div className="rounded-[8px] border border-border bg-surface2 p-3" key={balance.personId}>
                <div className="flex items-start justify-between gap-3">
                  <p className="font-medium text-text">{balance.personName}</p>
                  <span className={`text-sm font-semibold ${balanceTone(balance.net)}`}>{balanceLabel(balance.net)}</span>
                </div>
                <p className={`mt-2 text-lg font-semibold ${balanceTone(balance.net)}`}>{formatCurrency(Math.abs(balance.net))}</p>
                <p className="mt-1 text-xs text-subtle">
                  Cobra {formatCurrency(balance.receivable)} · Paga {formatCurrency(balance.payable)}
                </p>
              </div>
            ))}
            {personObligationBalances.length === 0 ? (
              <p className="rounded-[8px] border border-border bg-surface2 px-4 py-5 text-sm text-muted sm:col-span-2 xl:col-span-3">
                No hay saldos cruzados pendientes por persona.
              </p>
            ) : null}
          </div>
        </div>
      </section>

      <section className="panel p-4">
        <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
          <div className="rounded-[8px] border border-accent/40 bg-accent/5 p-4">
            <p className="text-xs font-semibold uppercase text-accent">Me deben</p>
            <h2 className="mt-1 text-base font-semibold">Cuenta por cobrar</h2>
            <p className="mt-1 text-sm text-muted">Registra plata que alguien te debe sin convertirla en ingreso todavia.</p>
            <div className="mt-3 space-y-3">
              <label className="block text-xs text-subtle">
                Persona
                <select className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setReceivableForm((current) => ({ ...current, personId: event.target.value }))} value={receivableForm.personId}>
                  <option value="">Persona</option>
                  {people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}
                </select>
              </label>
              <label className="block text-xs text-subtle">
                Monto a cobrar
                <input className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" inputMode="decimal" onChange={(event) => setReceivableForm((current) => ({ ...current, amount: event.target.value }))} placeholder="30000" value={receivableForm.amount} />
              </label>
              <label className="block text-xs text-subtle">
                Motivo
                <input className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setReceivableForm((current) => ({ ...current, title: event.target.value }))} placeholder="Clase pendiente, compra compartida..." value={receivableForm.title} />
              </label>
              <label className="block text-xs text-subtle">
                Vencimiento opcional
                <input className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setReceivableForm((current) => ({ ...current, dueAt: event.target.value }))} type="datetime-local" value={receivableForm.dueAt} />
              </label>
              <textarea className="focus-ring min-h-20 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setReceivableForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Notas opcionales" value={receivableForm.notes} />
              <button className="focus-ring w-full rounded-[8px] bg-accent px-3 py-2 text-sm font-semibold text-black" onClick={createReceivable} type="button">
                Crear cuenta por cobrar
              </button>
            </div>
          </div>
          <div className="space-y-3">
            <div className="panel-tight p-3">
              <div className="flex flex-col gap-2 xl:flex-row xl:items-end">
                <label className="min-w-0 flex-1 text-xs text-subtle">
                  Buscar persona o motivo
                  <input
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    onChange={(event) => setReceivablePaymentFilter((current) => ({ ...current, q: event.target.value }))}
                    placeholder="Clase, almuerzo..."
                    value={receivablePaymentFilter.q}
                  />
                </label>
                <label className="min-w-0 flex-1 text-xs text-subtle">
                  Persona
                  <select
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    onChange={(event) => setReceivablePaymentFilter((current) => ({ ...current, personId: event.target.value }))}
                    value={receivablePaymentFilter.personId}
                  >
                    <option value="">Todas</option>
                    {people.map((person) => (
                      <option key={person.id} value={person.id}>
                        {person.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="min-w-0 flex-1 text-xs text-subtle">
                  Transferencia opcional
                  <select
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    onChange={(event) => setReceivablePaymentFilter((current) => ({ ...current, transactionId: event.target.value }))}
                    value={receivablePaymentFilter.transactionId}
                  >
                    <option value="">Sin enlazar</option>
                    {linkableTransactions.map((transaction) => (
                      <option key={transaction.id} value={transaction.id}>
                        {formatDateLabel(transaction.occurred_at)} · {transaction.counterparty ?? transaction.merchant_name ?? transaction.transaction_type} ·{" "}
                        {formatCurrency(Number(transaction.amount), transaction.currency)}
                      </option>
                    ))}
                  </select>
                </label>
                <button className="focus-ring rounded-[8px] bg-accent px-4 py-2 text-sm font-semibold text-black" onClick={linkReceivablePayments} type="button">
                  Aplicar seleccionadas
                </button>
              </div>
            </div>
            {filteredReceivables.map((receivable) => (
              <div className="rounded-[8px] border border-accent/20 bg-surface2 p-3" key={receivable.id}>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-text">{receivable.title}</p>
                      <ObligationStatusBadge status={receivable.status} />
                    </div>
                    <p className="mt-1 text-2xl font-semibold text-accent">{formatCurrency(toMoney(receivable.remaining_amount), receivable.currency)}</p>
                    <p className="text-sm text-muted">{receivable.person.name} me debe este remanente.</p>
                  </div>
                  <div className="flex flex-wrap gap-2 sm:justify-end">
                    <input className="focus-ring w-28 rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setPaymentDrafts((current) => ({ ...current, [receivable.id]: event.target.value }))} placeholder="Abono" value={paymentDrafts[receivable.id] ?? ""} />
                    <button className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-text" onClick={() => payReceivable(receivable, paymentDrafts[receivable.id] ?? "")} type="button">Abonar</button>
                    <button className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-accent" onClick={() => payReceivable(receivable, receivable.remaining_amount)} type="button">Pagar total</button>
                    <button
                      aria-label={`Detalle cuenta por cobrar ${receivable.title}`}
                      className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-accent"
                      onClick={() => setSelectedObligation({ kind: "receivable", obligation: receivable })}
                      type="button"
                    >
                      Detalle
                    </button>
                  </div>
                </div>
              </div>
            ))}
            {filteredReceivables.length === 0 && (
              <p className="rounded-[8px] border border-border bg-surface2 px-4 py-5 text-sm text-muted">
                No hay cuentas por cobrar pendientes con esos filtros.
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="panel p-4">
        <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
          <div className="rounded-[8px] border border-danger/40 bg-danger/5 p-4">
            <p className="text-xs font-semibold uppercase text-danger">Debo pagar</p>
            <h2 className="mt-1 text-base font-semibold">Cuenta por pagar</h2>
            <p className="mt-1 text-sm text-muted">Registra plata que tu tienes que pagar sin inflarla como gasto automaticamente.</p>
            <div className="mt-3 space-y-3">
              <label className="block text-xs text-subtle">
                Persona
                <select className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setPayableForm((current) => ({ ...current, personId: event.target.value }))} value={payableForm.personId}>
                  <option value="">Persona</option>
                  {people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}
                </select>
              </label>
              <label className="block text-xs text-subtle">
                Monto a pagar
                <input className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" inputMode="decimal" onChange={(event) => setPayableForm((current) => ({ ...current, amount: event.target.value }))} placeholder="15000" value={payableForm.amount} />
              </label>
              <label className="block text-xs text-subtle">
                Motivo
                <input className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setPayableForm((current) => ({ ...current, title: event.target.value }))} placeholder="Cuota pendiente, arriendo..." value={payableForm.title} />
              </label>
              <label className="block text-xs text-subtle">
                Vencimiento opcional
                <input className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setPayableForm((current) => ({ ...current, dueAt: event.target.value }))} type="datetime-local" value={payableForm.dueAt} />
              </label>
              <textarea className="focus-ring min-h-20 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setPayableForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Notas opcionales" value={payableForm.notes} />
              <button className="focus-ring w-full rounded-[8px] bg-danger px-3 py-2 text-sm font-semibold text-white" onClick={createPayable} type="button">
                Crear cuenta por pagar
              </button>
            </div>

            <div className="mt-4 rounded-[8px] border border-border bg-surface2 p-3">
              <h3 className="text-sm font-semibold">Compensar con cuenta por cobrar</h3>
              <div className="mt-3 space-y-2">
                <select className="focus-ring w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setOffsetForm((current) => ({ ...current, personId: event.target.value, receivableId: "", payableId: "" }))} value={offsetForm.personId}>
                  <option value="">Persona</option>
                  {people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}
                </select>
                <select className="focus-ring w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setOffsetForm((current) => ({ ...current, receivableId: event.target.value }))} value={offsetForm.receivableId}>
                  <option value="">Cuenta por cobrar</option>
                  {offsetReceivables.map((receivable) => <option key={receivable.id} value={receivable.id}>{receivable.title} · {formatCurrency(Number(receivable.remaining_amount), receivable.currency)}</option>)}
                </select>
                <select className="focus-ring w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setOffsetForm((current) => ({ ...current, payableId: event.target.value }))} value={offsetForm.payableId}>
                  <option value="">Cuenta por pagar</option>
                  {offsetPayables.map((payable) => <option key={payable.id} value={payable.id}>{payable.title} · {formatCurrency(Number(payable.remaining_amount), payable.currency)}</option>)}
                </select>
                <input className="focus-ring w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setOffsetForm((current) => ({ ...current, amount: event.target.value }))} placeholder="Monto opcional; vacio usa el maximo posible" value={offsetForm.amount} />
                <button className="focus-ring w-full rounded-[8px] bg-accent px-3 py-2 text-sm font-semibold text-black" onClick={offsetObligations} type="button">
                  Compensar saldos
                </button>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="panel-tight p-3">
              <div className="flex flex-col gap-2 xl:flex-row xl:items-end">
                <label className="min-w-0 flex-1 text-xs text-subtle">
                  Buscar persona o motivo
                  <input
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    onChange={(event) => setPayablePaymentFilter((current) => ({ ...current, q: event.target.value }))}
                    placeholder="Persona, arriendo, cuota..."
                    value={payablePaymentFilter.q}
                  />
                </label>
                <label className="min-w-0 flex-1 text-xs text-subtle">
                  Persona
                  <select
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    onChange={(event) => setPayablePaymentFilter((current) => ({ ...current, personId: event.target.value }))}
                    value={payablePaymentFilter.personId}
                  >
                    <option value="">Todas</option>
                    {people.map((person) => (
                      <option key={person.id} value={person.id}>
                        {person.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="min-w-0 flex-1 text-xs text-subtle">
                  Transferencia opcional
                  <select
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    onChange={(event) => setPayablePaymentFilter((current) => ({ ...current, transactionId: event.target.value }))}
                    value={payablePaymentFilter.transactionId}
                  >
                    <option value="">Sin enlazar</option>
                    {outgoingLinkableTransactions.map((transaction) => (
                      <option key={transaction.id} value={transaction.id}>
                        {formatDateLabel(transaction.occurred_at)} · {transaction.counterparty ?? transaction.merchant_name ?? transaction.transaction_type} ·{" "}
                        {formatCurrency(Number(transaction.amount), transaction.currency)}
                      </option>
                    ))}
                  </select>
                </label>
                <button className="focus-ring rounded-[8px] bg-accent px-4 py-2 text-sm font-semibold text-black" onClick={linkPayablePayments} type="button">
                  Aplicar seleccionadas
                </button>
              </div>
            </div>
            {filteredPayables.map((payable) => (
              <div className="rounded-[8px] border border-danger/20 bg-surface2 p-3" key={payable.id}>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-text">{payable.title}</p>
                      <ObligationStatusBadge status={payable.status} />
                    </div>
                    <p className="mt-1 text-2xl font-semibold text-danger">{formatCurrency(toMoney(payable.remaining_amount), payable.currency)}</p>
                    <p className="text-sm text-muted">Debo pagarle este remanente a {payable.person.name}.</p>
                  </div>
                  <div className="flex flex-wrap gap-2 sm:justify-end">
                    <input className="focus-ring w-28 rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setPayablePaymentDrafts((current) => ({ ...current, [payable.id]: event.target.value }))} placeholder="Pago" value={payablePaymentDrafts[payable.id] ?? ""} />
                    <button className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-text" onClick={() => payPayable(payable, payablePaymentDrafts[payable.id] ?? "")} type="button">Abonar</button>
                    <button className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-accent" onClick={() => payPayable(payable, payable.remaining_amount)} type="button">Pagar total</button>
                    <button
                      aria-label={`Detalle cuenta por pagar ${payable.title}`}
                      className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-danger"
                      onClick={() => setSelectedObligation({ kind: "payable", obligation: payable })}
                      type="button"
                    >
                      Detalle
                    </button>
                  </div>
                </div>
              </div>
            ))}
            {filteredPayables.length === 0 && (
              <p className="rounded-[8px] border border-border bg-surface2 px-4 py-5 text-sm text-muted">
                No hay cuentas por pagar pendientes con esos filtros.
              </p>
            )}
          </div>
        </div>
      </section>
      </>
      ) : null}

      <Modal
        onClose={() => setSelectedTransaction(null)}
        open={selectedTransaction !== null}
        title={selectedTransaction ? `Detalle movimiento ${transactionTitle(selectedTransaction)}` : "Detalle de movimiento"}
      >
        {selectedTransaction ? (
          <div className="space-y-4">
            <TransactionDetailContent transaction={selectedTransaction} />
            <div className="flex flex-col-reverse gap-2 border-t border-border pt-3 sm:flex-row sm:justify-end">
              <button className="focus-ring rounded-[8px] border border-border px-4 py-2 text-sm text-muted hover:text-text" onClick={() => setSelectedTransaction(null)} type="button">
                Cerrar
              </button>
              <button
                className="focus-ring rounded-[8px] bg-accent px-4 py-2 text-sm font-semibold text-black"
                onClick={() => {
                  const transaction = selectedTransaction;
                  setSelectedTransaction(null);
                  openEdit(transaction);
                }}
                type="button"
              >
                Editar movimiento
              </button>
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal
        onClose={() => setSelectedObligation(null)}
        open={selectedObligation !== null}
        title={
          selectedObligation
            ? `Detalle ${selectedObligation.kind === "receivable" ? "cuenta por cobrar" : "cuenta por pagar"}`
            : "Detalle de obligacion"
        }
      >
        {selectedObligation ? <ObligationDetailContent detail={selectedObligation} /> : null}
      </Modal>

      <Drawer onClose={closeEdit} open={editing !== null} title="Editar movimiento">
        <div className="space-y-5 pb-8">
          <div className="rounded-[8px] border border-border bg-surface2 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-wide text-subtle">Movimiento seleccionado</p>
                <h3 className="mt-1 truncate text-xl font-semibold text-text">{editMovementTitle}</h3>
                <p className="mt-1 text-sm text-muted">
                  {transactionTypeLabels.get(editForm.transactionType) ?? editForm.transactionType} · {editSelectedCategory?.name ?? "Sin categoria"} ·{" "}
                  {formatDateLabel(new Date(editForm.occurredAt).toISOString())}
                </p>
              </div>
              <div className="shrink-0 rounded-[8px] border border-border bg-surface px-3 py-2 text-right">
                <p className="text-xs text-subtle">Monto</p>
                <p className="text-lg font-semibold text-text">{formatCurrency(Number(editForm.amount || 0), editForm.currency)}</p>
                {editForm.currency === "USD" && editForm.amountClp ? (
                  <p className="mt-1 text-xs text-subtle">Eq. {formatCurrency(Number(editForm.amountClp), "CLP")}</p>
                ) : null}
              </div>
            </div>
            <div className="mt-3 grid gap-2 text-xs text-muted sm:grid-cols-3">
              <span className="rounded-[8px] border border-border bg-surface px-2 py-1">
                Cuenta: {editSelectedAccount ? financialAccountLabel(editSelectedAccount) : "Sin cuenta"}
              </span>
              <span className="rounded-[8px] border border-border bg-surface px-2 py-1">
                Persona: {editSelectedPerson?.name ?? "Sin persona"}
              </span>
              <span className="rounded-[8px] border border-border bg-surface px-2 py-1">
                Inversion: {editSelectedInvestmentAccount ? investmentAccountLabel(editSelectedInvestmentAccount) : "Sin inversion"}
              </span>
            </div>
          </div>

          <section className="rounded-[8px] border border-border bg-surface2 p-4">
            <h3 className="text-sm font-semibold text-text">Esenciales</h3>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-subtle">
                Tipo de movimiento
                <select
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                  onChange={(event) => setEditForm((current) => ({ ...current, transactionType: event.target.value as TransactionType }))}
                  value={editForm.transactionType}
                >
                  {transactionTypes.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-subtle">
                Cuando ocurrio
                <input
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                  onChange={(event) => setEditForm((current) => ({ ...current, occurredAt: event.target.value }))}
                  type="datetime-local"
                  value={editForm.occurredAt}
                />
              </label>
              <label className="text-xs text-subtle">
                Monto
                <div className="mt-1 grid grid-cols-[1fr_84px] gap-2">
                  <input
                    className="focus-ring w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    inputMode="decimal"
                    onChange={(event) => setEditForm((current) => ({ ...current, amount: parseCurrencyInput(event.target.value, current.currency) }))}
                    placeholder={editForm.currency === "USD" ? "22.00" : "$12.990"}
                    value={formatCurrencyInput(editForm.amount, editForm.currency)}
                  />
                  <select
                    className="focus-ring rounded-[8px] border border-border bg-surface px-2 py-2 text-sm text-text"
                    onChange={(event) => {
                      const currency = event.target.value as CurrencyCode;
                      setEditForm((current) => ({
                        ...current,
                        currency,
                        amount: parseCurrencyInput(current.amount, currency),
                        amountClp: currency === "CLP" ? "" : current.amountClp,
                        financialAccountId: financialAccounts.some((account) => account.id === Number(current.financialAccountId) && account.currency === currency)
                          ? current.financialAccountId
                          : ""
                      }));
                    }}
                    value={editForm.currency}
                  >
                    {currencyOptions.map((currency) => (
                      <option key={currency} value={currency}>
                        {currency}
                      </option>
                    ))}
                  </select>
                </div>
                {editForm.currency === "USD" ? (
                  <input
                    className="focus-ring mt-2 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    inputMode="numeric"
                    onChange={(event) => setEditForm((current) => ({ ...current, amountClp: parseCurrencyInput(event.target.value, "CLP") }))}
                    placeholder="Equivalente CLP opcional"
                    value={formatCurrencyInput(editForm.amountClp, "CLP")}
                  />
                ) : null}
              </label>
              <label className="text-xs text-subtle">
                Estado
                <select
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                  onChange={(event) => setEditForm((current) => ({ ...current, status: event.target.value as TransactionStatus }))}
                  value={editForm.status}
                >
                  {statuses.map((status) => (
                    <option key={status.value} value={status.value}>
                      {status.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </section>

          <section className="rounded-[8px] border border-border bg-surface2 p-4">
            <h3 className="text-sm font-semibold text-text">Origen y motivo</h3>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-subtle">
                Comercio o lugar
                <input
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                  onChange={(event) => setEditForm((current) => ({ ...current, merchantName: event.target.value }))}
                  placeholder={editUsesPersonContext ? "Opcional" : "Comercio, app o lugar"}
                  value={editForm.merchantName}
                />
              </label>
              <label className="text-xs text-subtle">
                Persona, origen o destino
                <input
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                  onChange={(event) => setEditForm((current) => ({ ...current, counterparty: event.target.value }))}
                  placeholder={editUsesPersonContext ? "Persona o contraparte" : "Opcional"}
                  value={editForm.counterparty}
                />
              </label>
            </div>
            <label className="mt-3 block text-xs text-subtle">
              Motivo / descripcion
              <input
                className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                onChange={(event) => setEditForm((current) => ({ ...current, description: event.target.value }))}
                placeholder="Ej: clase de matematica, pago tarjeta, compra supermercado"
                value={editForm.description}
              />
            </label>
            <label className="mt-3 block text-xs text-subtle">
              Nota interna
              <textarea
                className="focus-ring mt-1 min-h-24 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                onChange={(event) => setEditForm((current) => ({ ...current, notes: event.target.value }))}
                placeholder="Contexto extra, comprobante, aclaraciones..."
                value={editForm.notes}
              />
            </label>
          </section>

          <section className="rounded-[8px] border border-border bg-surface2 p-4">
            <h3 className="text-sm font-semibold text-text">Clasificacion, persona y cuentas</h3>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-subtle">
                Categoria
                <select
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                  onChange={(event) => setEditForm((current) => ({ ...current, categoryId: event.target.value }))}
                  value={editForm.categoryId}
                >
                  <option value="">Sin categoria</option>
                  {visibleEditCategories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-subtle">
                Relacion
                <select
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                  onChange={(event) => setEditForm((current) => ({ ...current, relationshipCategory: event.target.value as TransactionRelationshipCategory }))}
                  value={editForm.relationshipCategory}
                >
                  {relationshipCategories.map((category) => (
                    <option key={category.value} value={category.value}>
                      {category.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-subtle">
                Persona asociada
                <select
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                  onChange={(event) => setEditForm((current) => ({ ...current, personId: event.target.value }))}
                  value={editForm.personId}
                >
                  <option value="">Sin persona</option>
                  {people.map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-subtle">
                {editForm.transactionType === "internal_transfer" ? "Cuenta de origen" : "Cuenta o tarjeta donde paso"}
                <select
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                  onChange={(event) => setEditForm((current) => ({ ...current, financialAccountId: event.target.value }))}
                  value={editForm.financialAccountId}
                >
                  <option value="">Sin cuenta</option>
                  {compatibleEditFinancialAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {financialAccountLabel(account)}
                    </option>
                  ))}
                </select>
              </label>
              {editForm.transactionType === "internal_transfer" ? (
                <label className="text-xs text-subtle">
                  Cuenta de destino
                  <select
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    onChange={(event) => setEditForm((current) => ({ ...current, destinationAccountId: event.target.value }))}
                    value={editForm.destinationAccountId}
                  >
                    <option value="">Elegir cuenta</option>
                    {financialAccounts
                      .filter((account) => String(account.id) !== editForm.financialAccountId)
                      .map((account) => (
                        <option key={account.id} value={account.id}>
                          {financialAccountLabel(account)}
                        </option>
                      ))}
                  </select>
                </label>
              ) : null}
              {editForm.transactionType === "internal_transfer" && editSelectedDestinationAccount && editSelectedDestinationAccount.currency !== editForm.currency ? (
                <label className="text-xs text-subtle sm:col-span-2">
                  Monto recibido en {editSelectedDestinationAccount.currency}
                  <input
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    inputMode="decimal"
                    onChange={(event) => setEditForm((current) => ({ ...current, destinationAmount: event.target.value }))}
                    placeholder={`Monto en ${editSelectedDestinationAccount.currency}`}
                    value={editForm.destinationAmount}
                  />
                </label>
              ) : null}
              <label className="text-xs text-subtle sm:col-span-2">
                Cuenta de inversion
                <select
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={!["investment", "disinvestment"].includes(editForm.transactionType)}
                  onChange={(event) => setEditForm((current) => ({ ...current, investmentAccountId: event.target.value }))}
                  value={editForm.investmentAccountId}
                >
                  <option value="">Sin inversion</option>
                  {investmentAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {investmentAccountLabel(account)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </section>

          <section className="rounded-[8px] border border-border bg-surface2 p-4">
            <h3 className="text-sm font-semibold text-text">Obligaciones enlazadas</h3>
            <p className="mt-1 text-xs text-subtle">Solo enlaza el movimiento. Los pagos de saldos pendientes se registran desde el flujo de obligaciones.</p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-subtle">
                Cuenta por cobrar
                <select
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={!editCanUseReceivable}
                  onChange={(event) => setEditForm((current) => ({ ...current, receivableId: event.target.value }))}
                  value={editForm.receivableId}
                >
                  <option value="">Sin enlace</option>
                  {receivables.map((receivable) => (
                    <option key={receivable.id} value={receivable.id}>
                      {receivable.person.name} · {receivable.title}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-subtle">
                Cuenta por pagar
                <select
                  className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={!editCanUsePayable}
                  onChange={(event) => setEditForm((current) => ({ ...current, payableId: event.target.value }))}
                  value={editForm.payableId}
                >
                  <option value="">Sin enlace</option>
                  {payables.map((payable) => (
                    <option key={payable.id} value={payable.id}>
                      {payable.person.name} · {payable.title}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </section>

          <section className="rounded-[8px] border border-border bg-surface2 p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-text">Desglose por categorias</h3>
                <p className="mt-1 text-xs text-subtle">Usalo para compras mixtas o repartos internos.</p>
              </div>
              <button
                className="focus-ring rounded-[8px] border border-border px-3 py-2 text-xs text-muted hover:text-text"
                onClick={() => setEditSplitDrafts((current) => [...current, { categoryId: "", amount: "", label: "" }])}
                type="button"
              >
                Agregar parte
              </button>
            </div>
            <div className="space-y-2">
              {editSplitDrafts.map((split, index) => (
                <div className="grid gap-2 sm:grid-cols-[1fr_120px_1fr_auto]" key={`${index}-${split.label}`}>
                  <select
                    className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    onChange={(event) =>
                      setEditSplitDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, categoryId: event.target.value } : item)))
                    }
                    value={split.categoryId}
                  >
                    <option value="">Categoria</option>
                    {visibleEditCategories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                  <input
                    className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    inputMode="decimal"
                    onChange={(event) =>
                      setEditSplitDrafts((current) =>
                        current.map((item, itemIndex) => (itemIndex === index ? { ...item, amount: parseCurrencyInput(event.target.value, editForm.currency) } : item))
                      )
                    }
                    placeholder="Monto"
                    value={formatCurrencyInput(split.amount, editForm.currency)}
                  />
                  <input
                    className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    onChange={(event) =>
                      setEditSplitDrafts((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, label: event.target.value } : item)))
                    }
                    placeholder="Etiqueta"
                    value={split.label}
                  />
                  <button
                    className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-danger"
                    onClick={() => setEditSplitDrafts((current) => current.filter((_, itemIndex) => itemIndex !== index))}
                    type="button"
                  >
                    <Trash2 aria-hidden="true" className="h-4 w-4" />
                  </button>
                </div>
              ))}
              {editSplitDrafts.length === 0 && <p className="rounded-[8px] border border-border bg-surface px-3 py-4 text-sm text-subtle">Sin desglose. Agrega partes si quieres repartir una compra mixta.</p>}
            </div>
          </section>

          <div className="sticky bottom-0 -mx-4 border-t border-border bg-surface/95 px-4 py-3">
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button className="focus-ring rounded-[8px] border border-border px-4 py-2 text-sm text-muted hover:text-text" onClick={closeEdit} type="button">
                Cancelar
              </button>
              <button className="focus-ring rounded-[8px] bg-accent px-4 py-2 text-sm font-semibold text-black" onClick={saveEdit} type="button">
                Guardar cambios
              </button>
            </div>
          </div>
        </div>
      </Drawer>
    </div>
  );
}
