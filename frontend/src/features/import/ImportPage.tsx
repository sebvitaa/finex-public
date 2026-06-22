import { CheckCircle2, Inbox, Plus, RefreshCw, SplitSquareHorizontal, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { GmailMessagePreviewTabs } from "../../components/GmailMessagePreviewTabs";
import { CategoryBadge } from "../../components/ui/CategoryBadge";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { api } from "../../lib/api";
import { formatCurrency, formatCurrencyInput, formatDateLabel, parseCurrencyInput } from "../../lib/format";
import type {
  CashflowDirection,
  CurrencyCode,
  GmailMessage,
  GmailStatus,
  ImportCandidate,
  Category,
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
  { value: "income", label: "Ingreso por clases" },
  { value: "transfer_in", label: "Transferencia recibida" },
  { value: "transfer_out", label: "Transferencia enviada" },
  { value: "internal_transfer", label: "Traspaso entre mis cuentas" },
  { value: "receivable_payment", label: "Pago de cuenta por cobrar" },
  { value: "payable_payment", label: "Pago de cuenta por pagar" },
  { value: "investment", label: "Inversion" },
  { value: "disinvestment", label: "Desinversion" },
  { value: "subscription", label: "Suscripcion" },
  { value: "refund", label: "Devolucion" }
];

const statuses: Array<{ value: TransactionStatus; label: string }> = [
  { value: "classified", label: "Clasificado" },
  { value: "needs_review", label: "Por revisar" },
  { value: "pending_payment", label: "Pendiente" },
  { value: "paid", label: "Pagado" },
  { value: "ignored", label: "Ignorado" }
];

const relationshipCategories: Array<{ value: TransactionRelationshipCategory; label: string }> = [
  { value: "ninguna", label: "Ninguna" },
  { value: "amigos", label: "Amigos" },
  { value: "trabajo", label: "Trabajo" },
  { value: "mi", label: "Mi" },
  { value: "novia", label: "Novia" }
];
const currencyOptions: CurrencyCode[] = ["CLP", "USD"];

type SplitDraft = {
  categoryId: string;
  amount: string;
  label: string;
};

type ReceivableAllocationDraft = {
  receivableId: string;
  amount: string;
};

type PayableAllocationDraft = {
  payableId: string;
  amount: string;
};

type InternalReceivableDraft = {
  personId: string;
  amount: string;
  title: string;
};

type InternalPayableDraft = {
  personId: string;
  amount: string;
  title: string;
};

type CandidateDraft = {
  candidate: ImportCandidate;
  amount: string;
  currency: CurrencyCode;
  amountClp: string;
  transactionType: TransactionType;
  categoryId: string;
  financialAccountId: string;
  destinationAccountId: string;
  destinationAmount: string;
  investmentAccountId: string;
  personId: string;
  receivableId: string;
  payableId: string;
  relationshipCategory: TransactionRelationshipCategory;
  receivableSearch: string;
  receivableAllocationAmount: string;
  receivableAllocations: ReceivableAllocationDraft[];
  payableSearch: string;
  payableAllocationAmount: string;
  payableAllocations: PayableAllocationDraft[];
  internalReceivables: InternalReceivableDraft[];
  internalPayables: InternalPayableDraft[];
  merchantName: string;
  counterparty: string;
  description: string;
  status: TransactionStatus;
  occurredAt: string;
  splits: SplitDraft[];
  saving: boolean;
};

function toId(value: string) {
  return value ? Number(value) : null;
}

function toLocalInputValue(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return new Date().toISOString().slice(0, 16);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function cashflowDirectionForType(transactionType: TransactionType): CashflowDirection {
  if (["income", "transfer_in", "receivable_payment", "refund", "disinvestment"].includes(transactionType)) {
    return "inflow";
  }
  if (["expense", "subscription", "transfer_out", "payable_payment", "loan_out", "investment"].includes(transactionType)) {
    return "outflow";
  }
  return "neutral";
}

function cashflowLabel(direction: CashflowDirection) {
  if (direction === "inflow") return "Ingreso";
  if (direction === "outflow") return "Egreso";
  return "Neutro";
}

function cashflowClass(direction: CashflowDirection) {
  if (direction === "inflow") return "border-accent/40 bg-accent/10 text-accent";
  if (direction === "outflow") return "border-danger/40 bg-danger/10 text-danger";
  return "border-border bg-surface2 text-muted";
}

function categoryOptionsFor(categories: Category[], transactionType: TransactionType) {
  const expectedKind = cashflowDirectionForType(transactionType) === "inflow" ? "income" : "expense";
  return categories.filter((category) => category.kind === expectedKind || category.kind === "both");
}

function isReceivableLinkType(transactionType: TransactionType) {
  return cashflowDirectionForType(transactionType) === "inflow";
}

function isPayableLinkType(transactionType: TransactionType) {
  return cashflowDirectionForType(transactionType) === "outflow";
}

function allocationTotal(draft: CandidateDraft) {
  return draft.receivableAllocations.reduce((total, allocation) => total + (Number(allocation.amount) || 0), 0);
}

function payableAllocationTotal(draft: CandidateDraft) {
  return draft.payableAllocations.reduce((total, allocation) => total + (Number(allocation.amount) || 0), 0);
}

function internalReceivableTotal(draft: CandidateDraft) {
  return draft.internalReceivables.reduce((total, item) => total + (Number(item.amount) || 0), 0);
}

function internalPayableTotal(draft: CandidateDraft) {
  return draft.internalPayables.reduce((total, item) => total + (Number(item.amount) || 0), 0);
}

function ownExpenseAmount(draft: CandidateDraft) {
  return Math.max(Number(draft.amount) - internalReceivableTotal(draft), 0);
}

function ownIncomeAmount(draft: CandidateDraft) {
  return Math.max(Number(draft.amount) - internalPayableTotal(draft), 0);
}

function createDraft(candidate: ImportCandidate): CandidateDraft {
  return {
    candidate,
    amount: candidate.amount,
    currency: candidate.currency,
    amountClp: candidate.amount_clp ?? "",
    transactionType: candidate.suggested_transaction_type,
    categoryId: candidate.suggested_category_id ? String(candidate.suggested_category_id) : "",
    financialAccountId: candidate.suggested_financial_account_id ? String(candidate.suggested_financial_account_id) : "",
    destinationAccountId: "",
    destinationAmount: "",
    investmentAccountId: candidate.suggested_investment_account_id ? String(candidate.suggested_investment_account_id) : "",
    personId: "",
    receivableId: "",
    payableId: "",
    relationshipCategory: "mi",
    receivableSearch: "",
    receivableAllocationAmount: "",
    receivableAllocations: [],
    payableSearch: "",
    payableAllocationAmount: "",
    payableAllocations: [],
    internalReceivables: [],
    internalPayables: [],
    merchantName: candidate.merchant_name ?? "",
    counterparty: candidate.counterparty ?? "",
    description: candidate.description ?? candidate.subject,
    status: candidate.status,
    occurredAt: toLocalInputValue(candidate.received_at),
    splits: candidate.suggested_splits.map((split) => ({
      categoryId: split.category_id ? String(split.category_id) : "",
      amount: split.amount,
      label: split.label ?? split.category_name ?? ""
    })),
    saving: false
  };
}

function candidateReceivedTime(candidate: ImportCandidate) {
  const time = Date.parse(candidate.received_at);
  return Number.isNaN(time) ? 0 : time;
}

function sortDraftsNewestFirst(drafts: CandidateDraft[]) {
  return [...drafts].sort((left, right) => {
    const byDate = candidateReceivedTime(right.candidate) - candidateReceivedTime(left.candidate);
    if (byDate !== 0) return byDate;
    return right.candidate.email_message_id - left.candidate.email_message_id;
  });
}

function gmailMessageStatusLabel(status: string) {
  if (status === "parsed") return "Candidato";
  if (status === "confirmed") return "Confirmado";
  if (status === "discarded") return "Ignorado";
  if (status === "parse_failed") return "Error parser";
  return status;
}

function gmailMessageStatusClass(status: string) {
  if (status === "parsed") return "border-info/40 bg-info/10 text-info";
  if (status === "confirmed") return "border-accent/40 bg-accent/10 text-accent";
  if (status === "discarded") return "border-border bg-surface2 text-muted";
  if (status === "parse_failed") return "border-warning/40 bg-warning/10 text-warning";
  return "border-border bg-surface2 text-muted";
}

function redactLocalCredentialsPath(pathValue?: string | null) {
  if (!pathValue) return "data/local/gmail_credentials.json";
  const marker = "data/local/";
  const markerIndex = pathValue.lastIndexOf(marker);
  if (markerIndex >= 0) return pathValue.slice(markerIndex);
  const fileName = pathValue.split(/[\\/]/).pop();
  return fileName ? `data/local/${fileName}` : "data/local/gmail_credentials.json";
}

type ImportPageMode = "import" | "review";

type ImportPageProps = {
  mode?: ImportPageMode;
};

export function ImportPage({ mode = "import" }: ImportPageProps) {
  const showPasteImport = mode === "import";
  const showMailbox = mode === "review";
  const [categories, setCategories] = useState<Category[]>([]);
  const [financialAccounts, setFinancialAccounts] = useState<FinancialAccount[]>([]);
  const [investmentAccounts, setInvestmentAccounts] = useState<InvestmentAccount[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [receivables, setReceivables] = useState<Receivable[]>([]);
  const [payables, setPayables] = useState<Payable[]>([]);
  const [rawText, setRawText] = useState("");
  const [drafts, setDrafts] = useState<CandidateDraft[]>([]);
  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null);
  const [gmailMessages, setGmailMessages] = useState<GmailMessage[]>([]);
  const [gmailQuery, setGmailQuery] = useState("");
  const [gmailMaxResults, setGmailMaxResults] = useState("5");
  const [gmailIncludeSpam, setGmailIncludeSpam] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [isGmailSyncing, setIsGmailSyncing] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const autoSyncRan = useRef(false);

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

  const loadGmailStatus = useCallback(async () => {
    const status = await api.gmailStatus();
    setGmailStatus(status);
    return status;
  }, []);

  const mergeCandidates = useCallback((candidates: ImportCandidate[]) => {
    setDrafts((current) => {
      const existingIds = new Set(current.map((draft) => draft.candidate.email_message_id));
      const incoming = candidates.filter((candidate) => !existingIds.has(candidate.email_message_id)).map(createDraft);
      return sortDraftsNewestFirst([...incoming, ...current]);
    });
  }, []);

  const loadGmailCandidates = useCallback(async () => {
    const candidates = await api.gmailCandidates(20);
    mergeCandidates(candidates);
    return candidates;
  }, [mergeCandidates]);

  const loadGmailMessages = useCallback(async () => {
    const messages = await api.gmailMessages(50);
    setGmailMessages(messages);
    return messages;
  }, []);

  useEffect(() => {
    let ignore = false;
    Promise.all([loadReferenceData(), loadGmailStatus(), loadGmailMessages()]).catch(() => {
      if (!ignore) setError("No pude cargar categorias, personas o cuentas por cobrar.");
    });
    return () => {
      ignore = true;
    };
  }, [loadGmailMessages, loadGmailStatus, loadReferenceData]);

  useEffect(() => {
    const refreshGmailStatus = () => {
      Promise.all([loadGmailStatus(), loadGmailMessages()]).catch(() => setError("No pude actualizar el estado de Gmail."));
    };

    window.addEventListener("focus", refreshGmailStatus);
    window.addEventListener("pageshow", refreshGmailStatus);
    return () => {
      window.removeEventListener("focus", refreshGmailStatus);
      window.removeEventListener("pageshow", refreshGmailStatus);
    };
  }, [loadGmailMessages, loadGmailStatus]);

  useEffect(() => {
    // Pending candidates live in FinEx once synced, so load them regardless of
    // the live Gmail connection. Otherwise an expired token hides every pending
    // movement waiting for approval.
    loadGmailCandidates().catch(() => setError("No pude cargar candidatos Gmail pendientes."));
  }, [loadGmailCandidates]);

  useEffect(() => {
    if (!gmailStatus?.connected || autoSyncRan.current) return;
    autoSyncRan.current = true;
    syncGmail("automatico");
  }, [gmailStatus?.connected]);

  const categoryByName = useMemo(() => {
    const lookup = new Map<string, Category>();
    categories.forEach((category) => lookup.set(category.name.toLowerCase(), category));
    return lookup;
  }, [categories]);

  const gmailMessageStats = useMemo(() => {
    return gmailMessages.reduce(
      (stats, message) => {
        if (message.parse_status === "parsed") stats.parsed += 1;
        else if (message.parse_status === "confirmed") stats.confirmed += 1;
        else if (message.parse_status === "discarded") stats.discarded += 1;
        else if (message.parse_status === "parse_failed") stats.parseFailed += 1;
        else stats.other += 1;
        return stats;
      },
      { confirmed: 0, discarded: 0, other: 0, parseFailed: 0, parsed: 0 }
    );
  }, [gmailMessages]);

  function updateDraft(emailMessageId: number, updater: (draft: CandidateDraft) => CandidateDraft) {
    setDrafts((current) => current.map((draft) => (draft.candidate.email_message_id === emailMessageId ? updater(draft) : draft)));
  }

  function addReceivableAllocation(emailMessageId: number) {
    updateDraft(emailMessageId, (draft) => {
      const receivable = receivables.find((item) => item.id === Number(draft.receivableId));
      if (!receivable) return draft;
      const remainingTransferAmount = Math.max(Number(draft.amount) - allocationTotal(draft), 0);
      const defaultAmount = Math.min(Number(receivable.remaining_amount), remainingTransferAmount || Number(receivable.remaining_amount));
      const amount = draft.receivableAllocationAmount || String(defaultAmount);
      return {
        ...draft,
        receivableAllocationAmount: "",
        receivableAllocations: [...draft.receivableAllocations, { receivableId: draft.receivableId, amount }]
      };
    });
  }

  function addPayableAllocation(emailMessageId: number) {
    updateDraft(emailMessageId, (draft) => {
      const payable = payables.find((item) => item.id === Number(draft.payableId));
      if (!payable) return draft;
      const remainingTransferAmount = Math.max(Number(draft.amount) - payableAllocationTotal(draft), 0);
      const defaultAmount = Math.min(Number(payable.remaining_amount), remainingTransferAmount || Number(payable.remaining_amount));
      const amount = draft.payableAllocationAmount || String(defaultAmount);
      return {
        ...draft,
        payableAllocationAmount: "",
        payableAllocations: [...draft.payableAllocations, { payableId: draft.payableId, amount }]
      };
    });
  }

  async function archiveGmailMessage(messageId: number) {
    try {
      await api.gmailSetMessageVisibility(messageId, false);
      setGmailMessages((current) => current.filter((message) => message.id !== messageId));
      setDrafts((current) => current.filter((draft) => draft.candidate.email_message_id !== messageId));
      setFeedback("Correo archivado en FinEx. Lo puedes restaurar desde Ajustes.");
      setError(null);
    } catch {
      setError("No pude archivar ese correo.");
    }
  }

  async function previewText() {
    if (!rawText.trim()) return;
    setIsLoading(true);
    try {
      const candidate = await api.importText(rawText);
      setDrafts((current) => sortDraftsNewestFirst([createDraft(candidate), ...current]));
      setFeedback("Correo previsualizado. Revisa tipo, categoria y desglose antes de guardar.");
      setError(null);
      setRawText("");
    } catch {
      setError("No pude detectar una transaccion en ese correo. Revisa que tenga monto y comercio.");
    } finally {
      setIsLoading(false);
    }
  }

  async function loadDemo() {
    setIsLoading(true);
    try {
      const candidates = await api.importDemo();
      setDrafts(sortDraftsNewestFirst(candidates.map(createDraft)));
      setFeedback("Dataset demo cargado como candidatos revisables.");
      setError(null);
    } catch {
      setError("No pude cargar el dataset demo.");
    } finally {
      setIsLoading(false);
    }
  }

  async function connectGmail() {
    try {
      const response = await api.gmailConnect();
      window.open(response.authorization_url, "_blank", "noopener,noreferrer");
      setFeedback(`Abri Google para autorizar Gmail. Redirect configurado: ${response.redirect_uri}`);
      setError(null);
    } catch {
      setError("No pude iniciar OAuth. Revisa que data/local/gmail_credentials.json exista y que el backend use el redirect correcto.");
    }
  }

  async function syncGmail(mode: "manual" | "automatico" = "manual") {
    if (isGmailSyncing) return;
    setIsGmailSyncing(true);
    try {
      const response = await api.gmailSync({
        max_results: Math.max(Number(gmailMaxResults) || 5, 1),
        query: gmailQuery.trim() || undefined,
        label_ids: gmailIncludeSpam ? ["INBOX", "SPAM"] : ["INBOX"],
        include_spam_trash: gmailIncludeSpam
      });
      if (response.candidates.length > 0) {
        mergeCandidates(response.candidates);
      }
      setFeedback(
        `Gmail ${mode}: ${response.candidates.length} candidatos, ${response.reprocessed_count ?? 0} reprocesados, ${response.ignored_count} irrelevantes, ${response.duplicate_count} duplicados.`
      );
      setError(null);
      await loadGmailStatus();
      await loadGmailMessages();
    } catch {
      setError("No pude sincronizar Gmail. Revisa la conexion, el token OAuth o las credenciales locales.");
    } finally {
      setIsGmailSyncing(false);
    }
  }

  async function disconnectGmail() {
    try {
      await api.gmailDisconnect();
      await loadGmailStatus();
      setFeedback("Gmail desconectado. El token local fue eliminado.");
      setError(null);
    } catch {
      setError("No pude desconectar Gmail.");
    }
  }

  function changeType(emailMessageId: number, transactionType: TransactionType) {
    updateDraft(emailMessageId, (draft) => {
      const categoryName =
        transactionType === "receivable_payment"
          ? "Cuentas por cobrar"
          : transactionType === "payable_payment"
            ? "Cuentas por pagar"
            : transactionType === "income"
              ? "Clases"
              : transactionType === "investment"
                ? "Inversiones"
                : transactionType === "disinvestment"
                  ? "Desinversiones"
                  : transactionType === "internal_transfer"
                    ? "Transferencias"
              : null;
      const category = categoryName ? categoryByName.get(categoryName.toLowerCase()) : null;
      return {
        ...draft,
        transactionType,
        categoryId: category ? String(category.id) : draft.categoryId,
        status: transactionType === "receivable_payment" || transactionType === "payable_payment" ? "paid" : draft.status
      };
    });
  }

  function applySupermarketTemplate(emailMessageId: number) {
    updateDraft(emailMessageId, (draft) => {
      const total = ownExpenseAmount(draft);
      const golosinas = categoryByName.get("golosinas");
      const comida = categoryByName.get("comida");
      const aseo = categoryByName.get("aseo y limpieza");
      const supermercado = categoryByName.get("supermercado");
      const golosinasAmount = Math.round(total * 0.2);
      const comidaAmount = Math.round(total * 0.5);
      const aseoAmount = Math.round(total * 0.24);
      const otrosAmount = Math.max(total - golosinasAmount - comidaAmount - aseoAmount, 0);
      return {
        ...draft,
        transactionType: "expense",
        categoryId: supermercado ? String(supermercado.id) : draft.categoryId,
        status: "classified",
        splits: [
          { categoryId: golosinas ? String(golosinas.id) : "", amount: String(golosinasAmount), label: "Golosinas" },
          { categoryId: comida ? String(comida.id) : "", amount: String(comidaAmount), label: "Comida" },
          { categoryId: aseo ? String(aseo.id) : "", amount: String(aseoAmount), label: "Aseo y limpieza" },
          { categoryId: supermercado ? String(supermercado.id) : "", amount: String(otrosAmount), label: "Otros" }
        ]
      };
    });
  }

  async function confirmDraft(emailMessageId: number) {
    const draft = drafts.find((item) => item.candidate.email_message_id === emailMessageId);
    if (!draft) return;
    const isInternalTransfer = draft.transactionType === "internal_transfer";
    if (isInternalTransfer) {
      if (!draft.financialAccountId || !draft.destinationAccountId) {
        setError("El traspaso entre cuentas necesita cuenta de origen y de destino.");
        return;
      }
      if (draft.financialAccountId === draft.destinationAccountId) {
        setError("La cuenta de destino debe ser distinta a la de origen.");
        return;
      }
      const destination = financialAccounts.find((account) => account.id === Number(draft.destinationAccountId));
      if (destination && destination.currency !== draft.currency && !draft.destinationAmount) {
        setError(`Indica el monto recibido en ${destination.currency} para el traspaso entre monedas distintas.`);
        return;
      }
    }
    updateDraft(emailMessageId, (current) => ({ ...current, saving: true }));
    try {
      const splits = draft.splits
        .filter((split) => split.amount && Number(split.amount) > 0)
        .map((split) => ({
          category_id: toId(split.categoryId),
          amount: split.amount,
          currency: draft.currency,
          label: split.label || null
        }));
      const receivablePayments = draft.receivableAllocations
        .filter((allocation) => allocation.receivableId && allocation.amount && Number(allocation.amount) > 0)
        .map((allocation) => ({
          receivable_id: Number(allocation.receivableId),
          amount: allocation.amount,
          notes: "Asignado desde importacion Gmail"
        }));
      const payablePayments = draft.payableAllocations
        .filter((allocation) => allocation.payableId && allocation.amount && Number(allocation.amount) > 0)
        .map((allocation) => ({
          payable_id: Number(allocation.payableId),
          amount: allocation.amount,
          notes: "Asignado desde importacion Gmail"
        }));
      const cashflowDirection = cashflowDirectionForType(draft.transactionType);
      const internalReceivables =
        cashflowDirection === "outflow"
          ? draft.internalReceivables
              .filter((item) => item.personId && item.amount && Number(item.amount) > 0)
              .map((item) => ({
                person_id: Number(item.personId),
                title: item.title || `Parte de ${draft.merchantName || draft.candidate.subject}`,
                amount: item.amount,
                notes: "Cuenta por cobrar interna creada desde compra importada"
              }))
          : [];
      const internalPayables =
        cashflowDirection === "inflow"
          ? draft.internalPayables
              .filter((item) => item.personId && item.amount && Number(item.amount) > 0)
              .map((item) => ({
                person_id: Number(item.personId),
                title: item.title || `Parte de ${draft.counterparty || draft.candidate.subject}`,
                amount: item.amount,
                notes: "Cuenta por pagar interna creada desde ingreso importado"
              }))
          : [];
      const financialAccountId = toId(draft.financialAccountId);
      const hasAccountDetection = Boolean(
        draft.candidate.detected_account_institution ||
          draft.candidate.detected_account_type ||
          draft.candidate.detected_account_last_four ||
          draft.candidate.account_detection_reason
      );
      const accountDetectionMethod =
        financialAccountId && draft.candidate.suggested_financial_account_id && financialAccountId !== draft.candidate.suggested_financial_account_id
          ? "manual_correction"
          : hasAccountDetection
            ? "email_parser"
            : financialAccountId
              ? "manual"
              : null;
      await api.confirmImport({
        email_message_id: draft.candidate.email_message_id,
        import_run_id: draft.candidate.import_run_id,
        occurred_at: new Date(draft.occurredAt).toISOString(),
        amount: draft.amount,
        currency: draft.currency,
        original_amount: draft.amount,
        original_currency: draft.currency,
        amount_clp: draft.currency === "CLP" ? draft.amount : draft.amountClp || null,
        exchange_rate: draft.currency === "USD" && draft.amountClp ? String(Number(draft.amountClp) / Number(draft.amount)) : null,
        exchange_rate_source: draft.candidate.exchange_rate_source,
        exchange_rate_date: draft.candidate.exchange_rate_date,
        currency_detection_confidence: draft.candidate.currency_detection_confidence,
        currency_detection_reason: draft.candidate.currency_detection_reason,
        merchant_name: draft.merchantName || null,
        counterparty: draft.counterparty || null,
        relationship_category: draft.relationshipCategory,
        financial_account_id: financialAccountId,
        destination_account_id: isInternalTransfer ? toId(draft.destinationAccountId) : null,
        destination_amount: isInternalTransfer && draft.destinationAmount ? draft.destinationAmount : null,
        investment_account_id: toId(draft.investmentAccountId),
        person_id: toId(draft.personId),
        receivable_id: receivablePayments.length > 0 ? null : toId(draft.receivableId),
        payable_id: payablePayments.length > 0 ? null : toId(draft.payableId),
        description: draft.description || null,
        subject: draft.candidate.subject,
        category_id: toId(draft.categoryId),
        transaction_type: draft.transactionType,
        status: draft.status,
        confidence: draft.candidate.confidence,
        classification_reason: draft.candidate.classification_reason,
        classification_method: draft.candidate.classification_method,
        account_detection_method: accountDetectionMethod,
        account_detection_confidence: draft.candidate.account_detection_confidence,
        account_detection_reason: draft.candidate.account_detection_reason,
        splits,
        receivable_payments: receivablePayments,
        payable_payments: payablePayments,
        internal_receivables: internalReceivables,
        internal_payables: internalPayables
      });
      setDrafts((current) => current.filter((item) => item.candidate.email_message_id !== emailMessageId));
      setFeedback("Movimiento importado y guardado.");
      setError(null);
      await Promise.all([loadReferenceData(), loadGmailMessages()]);
    } catch {
      updateDraft(emailMessageId, (current) => ({ ...current, saving: false }));
      setError("No pude confirmar la importacion. Si hay desglose, la suma debe coincidir con el monto.");
    }
  }

  async function discardDraft(emailMessageId: number) {
    const draft = drafts.find((item) => item.candidate.email_message_id === emailMessageId);
    if (!draft) return;
    try {
      await api.discardImport({
        email_message_id: draft.candidate.email_message_id,
        import_run_id: draft.candidate.import_run_id
      });
      setDrafts((current) => current.filter((item) => item.candidate.email_message_id !== emailMessageId));
      setFeedback("Correo descartado sin crear transaccion.");
      setError(null);
      await loadGmailMessages();
    } catch {
      setError("No pude descartar el correo.");
    }
  }

  return (
    <div className="space-y-4">
      {error && <div className="panel border-danger/50 px-4 py-3 text-sm text-danger">{error}</div>}
      {feedback && <div className="panel border-accent/50 px-4 py-3 text-sm text-accent">{feedback}</div>}

      <section className={showPasteImport ? "grid gap-4 xl:grid-cols-[0.9fr_1.1fr]" : "grid gap-4"}>
        {showPasteImport ? (
        <div className="panel p-4">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">Pegar correo</h2>
              <p className="text-sm text-muted">FinEx extrae monto, comercio, asunto y categoria sugerida antes de guardar.</p>
            </div>
            <Inbox aria-hidden="true" className="h-5 w-5 text-info" />
          </div>
          <textarea
            className="focus-ring min-h-72 w-full resize-y rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text placeholder:text-subtle"
            onChange={(event) => setRawText(event.target.value)}
            placeholder="From: Banco Demo&#10;Subject: Compra aprobada Lider por $42.000&#10;&#10;Comercio: Lider&#10;Monto: $42.000"
            value={rawText}
          />
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <button className="focus-ring rounded-[8px] bg-info px-4 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60" disabled={isLoading || !rawText.trim()} onClick={previewText} type="button">
              <RefreshCw aria-hidden="true" className="mr-2 inline h-4 w-4" />
              Previsualizar texto
            </button>
            <button className="focus-ring rounded-[8px] border border-border px-4 py-2 text-sm text-muted hover:text-text disabled:cursor-not-allowed disabled:opacity-60" disabled={isLoading} onClick={loadDemo} type="button">
              Cargar demo
            </button>
          </div>
        </div>
        ) : null}

        <div className="panel p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-base font-semibold">Gmail real</h2>
              <p className="mt-1 text-sm text-muted">
                {gmailStatus?.connected
                  ? "Cuenta conectada. FinEx trae candidatos, ignora correos irrelevantes y evita duplicados."
                  : gmailStatus?.client_configured
                    ? "Credenciales listas. Falta autorizar la cuenta con Google."
                    : "Falta colocar el archivo de credenciales OAuth en data/local/."}
              </p>
            </div>
            <span
              className={`inline-flex w-fit rounded-[8px] border px-2 py-1 text-xs ${
                gmailStatus?.connected
                  ? "border-accent/40 bg-accent/10 text-accent"
                  : gmailStatus?.client_configured
                    ? "border-warning/40 bg-warning/10 text-warning"
                    : "border-danger/40 bg-danger/10 text-danger"
              }`}
            >
              {gmailStatus?.connected ? "Conectado" : gmailStatus?.client_configured ? "Sin autorizar" : "Sin credenciales"}
            </span>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_110px]">
            <input
              className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text placeholder:text-subtle"
              onChange={(event) => setGmailQuery(event.target.value)}
              placeholder={gmailStatus?.default_query ?? "newer_than:30d"}
              value={gmailQuery}
            />
            <input
              className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
              inputMode="numeric"
              onChange={(event) => setGmailMaxResults(event.target.value)}
              value={gmailMaxResults}
            />
          </div>
          <label className="mt-3 flex w-fit items-center gap-2 text-sm text-muted">
            <input
              checked={gmailIncludeSpam}
              className="h-4 w-4 rounded border-border bg-surface2"
              onChange={(event) => setGmailIncludeSpam(event.target.checked)}
              type="checkbox"
            />
            Incluir spam donde Gmail haya dejado avisos bancarios
          </label>

          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <button className="focus-ring rounded-[8px] border border-border px-4 py-2 text-sm text-muted hover:text-text disabled:cursor-not-allowed disabled:opacity-60" disabled={!gmailStatus?.client_configured} onClick={connectGmail} type="button">
              Conectar Gmail
            </button>
            <button className="focus-ring rounded-[8px] bg-accent px-4 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60" disabled={!gmailStatus?.connected || isGmailSyncing} onClick={() => syncGmail("manual")} type="button">
              <RefreshCw aria-hidden="true" className="mr-2 inline h-4 w-4" />
              Actualizar Gmail
            </button>
            <button className="focus-ring rounded-[8px] border border-border px-4 py-2 text-sm text-muted hover:text-danger disabled:cursor-not-allowed disabled:opacity-60" disabled={!gmailStatus?.connected} onClick={disconnectGmail} type="button">
              Desconectar
            </button>
          </div>

          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <p className="min-w-0 truncate text-xs text-subtle">Credenciales: {redactLocalCredentialsPath(gmailStatus?.credentials_path)}</p>
            <p className="min-w-0 truncate text-xs text-subtle">
              Ultimo sync: {gmailStatus?.last_sync_at ? formatDateLabel(gmailStatus.last_sync_at) : "sin sincronizar"}
            </p>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="panel-tight p-3">
              <p className="text-xs uppercase tracking-wide text-subtle">Privacidad</p>
              <p className="mt-1 text-sm text-muted">Se guarda vista previa, hash y campos financieros. El token OAuth queda local en data/local/.</p>
            </div>
            <div className="panel-tight p-3">
              <p className="text-xs uppercase tracking-wide text-subtle">Bandeja</p>
              <p className="mt-1 text-sm text-muted">
                {drafts.length === 0 ? "Sin candidatos por ahora." : `${drafts.length} candidatos esperan confirmacion o descarte.`}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <div className="panel p-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-subtle">Revisión</p>
              <h2 className="mt-1 text-xl font-semibold">Candidatos por revisar</h2>
            </div>
            <span className="w-fit rounded-[8px] border border-info/40 bg-info/10 px-2 py-1 text-xs text-info">
              {drafts.length} pendientes
            </span>
          </div>
          {drafts.length === 0 && (
            <p className="mt-3 text-sm text-muted">
              No hay candidatos cargados en esta vista. Si la bandeja muestra candidatos existentes, usa Actualizar Gmail para reconstruirlos.
            </p>
          )}
        </div>
        {drafts.map((draft) => {
          const visibleCategories = categoryOptionsFor(categories, draft.transactionType);
          const selectedCategory = categories.find((category) => category.id === Number(draft.categoryId));
          const receivableSearch = draft.receivableSearch.trim().toLowerCase();
          const filteredReceivables = receivables.filter((receivable) => {
            if (Number(receivable.remaining_amount) <= 0) return false;
            if (!receivableSearch) return true;
            return `${receivable.person.name} ${receivable.title} ${receivable.notes ?? ""}`.toLowerCase().includes(receivableSearch);
          });
          const payableSearch = draft.payableSearch.trim().toLowerCase();
          const filteredPayables = payables.filter((payable) => {
            if (Number(payable.remaining_amount) <= 0) return false;
            if (!payableSearch) return true;
            return `${payable.person.name} ${payable.title} ${payable.notes ?? ""}`.toLowerCase().includes(payableSearch);
          });
          const assignedReceivableTotal = allocationTotal(draft);
          const unassignedReceivableAmount = Math.max(Number(draft.amount) - assignedReceivableTotal, 0);
          const assignedPayableTotal = payableAllocationTotal(draft);
          const unassignedPayableAmount = Math.max(Number(draft.amount) - assignedPayableTotal, 0);
          const ownExpense = ownExpenseAmount(draft);
          const ownIncome = ownIncomeAmount(draft);
          const usesPersonContext = ["income", "transfer_in", "transfer_out", "receivable_payment", "payable_payment"].includes(draft.transactionType);
          const contextValue = usesPersonContext ? draft.counterparty : draft.merchantName;
          const cashflowDirection = cashflowDirectionForType(draft.transactionType);
          const candidatePreview = draft.candidate.body_preview?.trim() || "";
          const candidateFullText = draft.candidate.body_text?.trim() || "";
          const showCandidateFullText = candidateFullText.length > 0 && candidateFullText !== candidatePreview;
          return (
            <article className="panel p-4" key={draft.candidate.email_message_id}>
              <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="truncate text-base font-semibold">{draft.candidate.subject}</h3>
                    <StatusBadge status={draft.status} />
                    <span
                      className={`rounded-[8px] border px-2 py-1 text-xs ${cashflowClass(cashflowDirection)}`}
                      title={`Detectado inicialmente: ${cashflowLabel(draft.candidate.cashflow_direction)}`}
                    >
                      {cashflowLabel(cashflowDirection)}
                    </span>
                    {draft.candidate.needs_split && (
                      <span className="rounded-[8px] border border-warning/40 bg-warning/10 px-2 py-1 text-xs text-warning">Por distribuir</span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-muted">
                    {draft.merchantName || draft.counterparty || "Origen por revisar"} · {formatDateLabel(draft.candidate.received_at)}
                  </p>
                  <p className="mt-2 line-clamp-2 text-sm text-subtle">{candidatePreview || "Sin resumen guardado."}</p>
                  {showCandidateFullText ? (
                    <details className="mt-3 rounded-[8px] border border-border bg-surface2 p-3">
                      <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-subtle">
                        Ver correo completo
                      </summary>
                      <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs leading-5 text-muted">
                        {candidateFullText}
                      </pre>
                    </details>
                  ) : null}
                </div>
                <div className="shrink-0 text-left xl:text-right">
                  <div className="grid grid-cols-[1fr_84px] gap-2 xl:w-64">
                    <input
                      className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-right text-lg font-semibold text-text"
                      inputMode="decimal"
                      onChange={(event) =>
                        updateDraft(draft.candidate.email_message_id, (current) => ({
                          ...current,
                          amount: parseCurrencyInput(event.target.value, current.currency)
                        }))
                      }
                      value={formatCurrencyInput(draft.amount, draft.currency)}
                    />
                    <select
                      className="focus-ring rounded-[8px] border border-border bg-surface2 px-2 py-2 text-sm text-text"
                      onChange={(event) => {
                        const currency = event.target.value as CurrencyCode;
                        updateDraft(draft.candidate.email_message_id, (current) => ({
                          ...current,
                          currency,
                          amount: parseCurrencyInput(current.amount, currency),
                          amountClp: currency === "CLP" ? "" : current.amountClp,
                          financialAccountId: financialAccounts.some((account) => account.id === Number(current.financialAccountId) && account.currency === currency)
                            ? current.financialAccountId
                            : ""
                        }));
                      }}
                      value={draft.currency}
                    >
                      {currencyOptions.map((currency) => (
                        <option key={currency} value={currency}>
                          {currency}
                        </option>
                      ))}
                    </select>
                  </div>
                  {draft.currency === "USD" ? (
                    <input
                      className="focus-ring mt-2 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-right text-sm text-text"
                      inputMode="numeric"
                      onChange={(event) =>
                        updateDraft(draft.candidate.email_message_id, (current) => ({
                          ...current,
                          amountClp: parseCurrencyInput(event.target.value, "CLP")
                        }))
                      }
                      placeholder="Equivalente CLP"
                      value={formatCurrencyInput(draft.amountClp, "CLP")}
                    />
                  ) : null}
                  <p className="mt-1 text-xs text-subtle">{draft.candidate.classification_reason}</p>
                  {draft.candidate.currency_detection_reason ? (
                    <p className="mt-1 text-xs text-info">{draft.candidate.currency_detection_reason}</p>
                  ) : null}
                </div>
              </div>

              <div className="mt-4 grid gap-3 lg:grid-cols-4">
                <label className="text-sm text-muted">
                  Tipo
                  <select
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                    onChange={(event) => changeType(draft.candidate.email_message_id, event.target.value as TransactionType)}
                    value={draft.transactionType}
                  >
                    {transactionTypes.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm text-muted">
                  Categoria
                  <select
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                    onChange={(event) => updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, categoryId: event.target.value }))}
                    value={draft.categoryId}
                  >
                    <option value="">Sin categoria</option>
                    {visibleCategories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm text-muted">
                  Estado
                  <select
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                    onChange={(event) => updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, status: event.target.value as TransactionStatus }))}
                    value={draft.status}
                  >
                    {statuses.map((status) => (
                      <option key={status.value} value={status.value}>
                        {status.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm text-muted">
                  Fecha
                  <input
                    className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface2 px-3 py-2 text-text"
                    onChange={(event) => updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, occurredAt: event.target.value }))}
                    type="datetime-local"
                    value={draft.occurredAt}
                  />
                </label>
              </div>

              <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_auto]">
                <input
                  className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text placeholder:text-subtle"
                  onChange={(event) =>
                    updateDraft(draft.candidate.email_message_id, (current) =>
                      usesPersonContext
                        ? { ...current, counterparty: event.target.value, merchantName: "" }
                        : { ...current, merchantName: event.target.value, counterparty: "" }
                    )
                  }
                  placeholder={usesPersonContext ? "Persona u origen" : "Lugar o comercio"}
                  value={contextValue}
                />
                <span className="rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-muted">
                  {selectedCategory ? selectedCategory.name : "Sin categoria base"}
                </span>
              </div>

              <details className="mt-4 rounded-[8px] border border-border bg-surface2 p-3">
                <summary className="focus-ring cursor-pointer rounded-[8px] text-sm font-semibold text-text">
                  Detalles de confirmacion
                  <span className="ml-2 text-xs font-normal text-subtle">relacion, persona, obligaciones y cuentas</span>
                </summary>
                <div className="mt-3 grid gap-3 lg:grid-cols-3">
                  <select
                    className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    onChange={(event) =>
                      updateDraft(draft.candidate.email_message_id, (current) => ({
                        ...current,
                        relationshipCategory: event.target.value as TransactionRelationshipCategory
                      }))
                    }
                    value={draft.relationshipCategory}
                  >
                    {relationshipCategories.map((category) => (
                      <option key={category.value} value={category.value}>
                        {category.label}
                      </option>
                    ))}
                  </select>
                  <select
                    className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                    onChange={(event) => updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, personId: event.target.value }))}
                    value={draft.personId}
                  >
                    <option value="">Sin persona</option>
                    {people.map((person) => (
                      <option key={person.id} value={person.id}>
                        {person.name}
                      </option>
                    ))}
                  </select>
                  {!isReceivableLinkType(draft.transactionType) && !isPayableLinkType(draft.transactionType) ? (
                    <div className="rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-muted">
                      Sin obligaciones para este tipo
                    </div>
                  ) : isReceivableLinkType(draft.transactionType) ? (
                    <select
                      className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                      onChange={(event) => updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, receivableId: event.target.value }))}
                      value={draft.receivableId}
                    >
                      <option value="">Sin cuenta por cobrar</option>
                      {receivables.map((receivable) => (
                        <option key={receivable.id} value={receivable.id}>
                          {receivable.person.name} · {receivable.title}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <select
                      className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                      onChange={(event) => updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, payableId: event.target.value }))}
                      value={draft.payableId}
                    >
                      <option value="">Cuenta por pagar</option>
                      {payables.map((payable) => (
                        <option key={payable.id} value={payable.id}>
                          {payable.person.name} · {payable.title}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <input
                  className="focus-ring mt-3 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-subtle"
                  onChange={(event) => updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, description: event.target.value }))}
                  placeholder="Descripcion"
                  value={draft.description}
                />

                <div className="mt-3 grid gap-3 lg:grid-cols-2">
                  <label className="text-sm text-muted">
                    {draft.transactionType === "internal_transfer" ? "Cuenta de origen" : "Cuenta o tarjeta"}
                    <select
                      className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                      onChange={(event) =>
                        updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, financialAccountId: event.target.value }))
                      }
                      value={draft.financialAccountId}
                    >
                      <option value="">Sin cuenta asignada</option>
                      {financialAccounts.filter((account) => account.currency === draft.currency).map((account) => (
                        <option key={account.id} value={account.id}>
                          {account.name}{account.last_four ? ` · ${account.last_four}` : ""} · {account.currency}
                        </option>
                      ))}
                    </select>
                    {draft.candidate.account_detection_reason && (
                      <span className="mt-1 block text-xs text-subtle">
                        Sugerencia: {draft.candidate.suggested_financial_account_name ?? draft.candidate.account_detection_reason}
                      </span>
                    )}
                  </label>
                  {draft.transactionType === "internal_transfer" ? (
                    <label className="text-sm text-muted">
                      Cuenta de destino
                      <select
                        className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                        onChange={(event) =>
                          updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, destinationAccountId: event.target.value }))
                        }
                        value={draft.destinationAccountId}
                      >
                        <option value="">Elegir cuenta</option>
                        {financialAccounts
                          .filter((account) => String(account.id) !== draft.financialAccountId)
                          .map((account) => (
                            <option key={account.id} value={account.id}>
                              {account.name}{account.last_four ? ` · ${account.last_four}` : ""} · {account.currency}
                            </option>
                          ))}
                      </select>
                      {(() => {
                        const destination = financialAccounts.find((account) => account.id === Number(draft.destinationAccountId));
                        if (!destination || destination.currency === draft.currency) return null;
                        return (
                          <input
                            className="focus-ring mt-2 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                            inputMode="decimal"
                            onChange={(event) =>
                              updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, destinationAmount: event.target.value }))
                            }
                            placeholder={`Monto recibido en ${destination.currency}`}
                            value={draft.destinationAmount}
                          />
                        );
                      })()}
                    </label>
                  ) : draft.transactionType === "investment" || draft.transactionType === "disinvestment" ? (
                    <label className="text-sm text-muted">
                      Cuenta de inversion
                      <select
                        className="focus-ring mt-1 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                        onChange={(event) =>
                          updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, investmentAccountId: event.target.value }))
                        }
                        value={draft.investmentAccountId}
                      >
                        <option value="">Sin cuenta de inversion</option>
                        {investmentAccounts.map((account) => (
                          <option key={account.id} value={account.id}>
                            {account.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : (
                    <div className="rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-muted">
                      Sin cuenta de inversion para este tipo
                    </div>
                  )}
                </div>
              </details>

              {isReceivableLinkType(draft.transactionType) && (
                <div className="mt-4 panel-tight p-3">
                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div>
                      <h4 className="text-sm font-semibold">Asignar a cuentas por cobrar</h4>
                      <p className="mt-1 text-xs text-subtle">
                        Asignado: {formatCurrency(assignedReceivableTotal, draft.currency)} · Sin asignar:{" "}
                        {formatCurrency(unassignedReceivableAmount, draft.currency)}
                      </p>
                    </div>
                    <span className="w-fit rounded-[8px] border border-border bg-surface px-2 py-1 text-xs text-muted">
                      El pago puede ser parcial o repartido
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 lg:grid-cols-[1fr_1fr_120px_auto]">
                    <input
                      className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-subtle"
                      onChange={(event) =>
                        updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, receivableSearch: event.target.value }))
                      }
                      placeholder="Buscar persona o motivo"
                      value={draft.receivableSearch}
                    />
                    <select
                      className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                      onChange={(event) => updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, receivableId: event.target.value }))}
                      value={draft.receivableId}
                    >
                      <option value="">Seleccionar deuda</option>
                      {filteredReceivables.map((receivable) => (
                        <option key={receivable.id} value={receivable.id}>
                          {receivable.person.name} · {receivable.title} · {formatCurrency(Number(receivable.remaining_amount), receivable.currency)}
                        </option>
                      ))}
                    </select>
                    <input
                      className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                      inputMode="decimal"
                      onChange={(event) =>
                        updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, receivableAllocationAmount: event.target.value }))
                      }
                      placeholder="Monto"
                      value={draft.receivableAllocationAmount}
                    />
                    <button
                      className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-text"
                      onClick={() => addReceivableAllocation(draft.candidate.email_message_id)}
                      type="button"
                    >
                      Agregar
                    </button>
                  </div>
                  <div className="mt-3 space-y-2">
                    {draft.receivableAllocations.map((allocation, index) => {
                      const receivable = receivables.find((item) => item.id === Number(allocation.receivableId));
                      return (
                        <div className="grid gap-2 rounded-[8px] border border-border bg-surface px-3 py-2 md:grid-cols-[1fr_140px_auto]" key={`${allocation.receivableId}-${index}`}>
                          <p className="min-w-0 truncate text-sm text-muted">
                            {receivable ? `${receivable.person.name} · ${receivable.title}` : "Cuenta por cobrar"}
                          </p>
                          <input
                            className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                            inputMode="decimal"
                            onChange={(event) =>
                              updateDraft(draft.candidate.email_message_id, (current) => ({
                                ...current,
                                receivableAllocations: current.receivableAllocations.map((item, itemIndex) =>
                                  itemIndex === index ? { ...item, amount: event.target.value } : item
                                )
                              }))
                            }
                            value={allocation.amount}
                          />
                          <button
                            className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-danger"
                            onClick={() =>
                              updateDraft(draft.candidate.email_message_id, (current) => ({
                                ...current,
                                receivableAllocations: current.receivableAllocations.filter((_, itemIndex) => itemIndex !== index)
                              }))
                            }
                            type="button"
                          >
                            <X aria-hidden="true" className="h-4 w-4" />
                          </button>
                        </div>
                      );
                    })}
                    {draft.receivableAllocations.length === 0 && (
                      <p className="text-sm text-subtle">Selecciona una o varias deudas para enlazar este pago. Puede quedar parte del pago sin asignar.</p>
                    )}
                  </div>
                </div>
              )}

              {isPayableLinkType(draft.transactionType) && (
                <div className="mt-4 panel-tight p-3">
                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div>
                      <h4 className="text-sm font-semibold">Asignar a cuentas por pagar</h4>
                      <p className="mt-1 text-xs text-subtle">
                        Asignado: {formatCurrency(assignedPayableTotal, draft.currency)} · Sin asignar:{" "}
                        {formatCurrency(unassignedPayableAmount, draft.currency)}
                      </p>
                    </div>
                    <span className="w-fit rounded-[8px] border border-border bg-surface px-2 py-1 text-xs text-muted">
                      El pago puede ser parcial o repartido
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 lg:grid-cols-[1fr_1fr_120px_auto]">
                    <input
                      className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-subtle"
                      onChange={(event) =>
                        updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, payableSearch: event.target.value }))
                      }
                      placeholder="Buscar persona o motivo"
                      value={draft.payableSearch}
                    />
                    <select
                      className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                      onChange={(event) => updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, payableId: event.target.value }))}
                      value={draft.payableId}
                    >
                      <option value="">Seleccionar cuenta por pagar</option>
                      {filteredPayables.map((payable) => (
                        <option key={payable.id} value={payable.id}>
                          {payable.person.name} · {payable.title} · {formatCurrency(Number(payable.remaining_amount), payable.currency)}
                        </option>
                      ))}
                    </select>
                    <input
                      className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                      inputMode="decimal"
                      onChange={(event) =>
                        updateDraft(draft.candidate.email_message_id, (current) => ({ ...current, payableAllocationAmount: event.target.value }))
                      }
                      placeholder="Monto"
                      value={draft.payableAllocationAmount}
                    />
                    <button
                      className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-text"
                      onClick={() => addPayableAllocation(draft.candidate.email_message_id)}
                      type="button"
                    >
                      Agregar
                    </button>
                  </div>
                  <div className="mt-3 space-y-2">
                    {draft.payableAllocations.map((allocation, index) => {
                      const payable = payables.find((item) => item.id === Number(allocation.payableId));
                      return (
                        <div className="grid gap-2 rounded-[8px] border border-border bg-surface px-3 py-2 md:grid-cols-[1fr_140px_auto]" key={`${allocation.payableId}-${index}`}>
                          <p className="min-w-0 truncate text-sm text-muted">
                            {payable ? `${payable.person.name} · ${payable.title}` : "Cuenta por pagar"}
                          </p>
                          <input
                            className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                            inputMode="decimal"
                            onChange={(event) =>
                              updateDraft(draft.candidate.email_message_id, (current) => ({
                                ...current,
                                payableAllocations: current.payableAllocations.map((item, itemIndex) =>
                                  itemIndex === index ? { ...item, amount: event.target.value } : item
                                )
                              }))
                            }
                            value={allocation.amount}
                          />
                          <button
                            className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-danger"
                            onClick={() =>
                              updateDraft(draft.candidate.email_message_id, (current) => ({
                                ...current,
                                payableAllocations: current.payableAllocations.filter((_, itemIndex) => itemIndex !== index)
                              }))
                            }
                            type="button"
                          >
                            <X aria-hidden="true" className="h-4 w-4" />
                          </button>
                        </div>
                      );
                    })}
                    {draft.payableAllocations.length === 0 && (
                      <p className="text-sm text-subtle">Selecciona una o varias cuentas por pagar para enlazar esta transferencia enviada.</p>
                    )}
                  </div>
                </div>
              )}

              <details
                className="mt-4 panel-tight p-3"
                open={draft.candidate.needs_split || draft.splits.length > 0 || draft.internalReceivables.length > 0 || draft.internalPayables.length > 0}
              >
                <summary className="focus-ring cursor-pointer rounded-[8px] text-sm font-semibold text-text">
                  Desglose antes de guardar
                  <span className="ml-2 text-xs font-normal text-subtle">partes propias, por cobrar o por pagar</span>
                </summary>
                <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {selectedCategory ? <CategoryBadge color={selectedCategory.color} name={selectedCategory.name} /> : <span className="text-xs text-subtle">Sin categoria base</span>}
                      {cashflowDirection === "inflow" ? (
                        <span className="text-xs text-subtle">
                          Total: {formatCurrency(Number(draft.amount), draft.currency)} · Le debo:{" "}
                          {formatCurrency(internalPayableTotal(draft), draft.currency)} · Ingreso propio:{" "}
                          {formatCurrency(ownIncome, draft.currency)}
                        </span>
                      ) : (
                        <span className="text-xs text-subtle">
                          Total: {formatCurrency(Number(draft.amount), draft.currency)} · Me deben:{" "}
                          {formatCurrency(internalReceivableTotal(draft), draft.currency)} · Gasto propio:{" "}
                          {formatCurrency(ownExpense, draft.currency)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button className="focus-ring rounded-[8px] border border-border px-3 py-2 text-xs text-muted hover:text-text" onClick={() => applySupermarketTemplate(draft.candidate.email_message_id)} type="button">
                      <SplitSquareHorizontal aria-hidden="true" className="mr-1 inline h-4 w-4" />
                      Plantilla supermercado
                    </button>
                    <button
                      className="focus-ring rounded-[8px] border border-border px-3 py-2 text-xs text-muted hover:text-text"
                      onClick={() =>
                        updateDraft(draft.candidate.email_message_id, (current) => ({
                          ...current,
                          splits: [...current.splits, { categoryId: "", amount: "", label: "" }]
                        }))
                      }
                      type="button"
                    >
                      <Plus aria-hidden="true" className="mr-1 inline h-4 w-4" />
                      Agregar parte
                    </button>
                    {cashflowDirection === "outflow" && (
                      <button
                        className="focus-ring rounded-[8px] border border-border px-3 py-2 text-xs text-muted hover:text-text"
                        onClick={() =>
                          updateDraft(draft.candidate.email_message_id, (current) => ({
                            ...current,
                            internalReceivables: [...current.internalReceivables, { personId: "", amount: "", title: "Parte compra supermercado" }]
                          }))
                        }
                        type="button"
                      >
                        <Plus aria-hidden="true" className="mr-1 inline h-4 w-4" />
                        Me deben parte
                      </button>
                    )}
                    {cashflowDirection === "inflow" && (
                      <button
                        className="focus-ring rounded-[8px] border border-border px-3 py-2 text-xs text-muted hover:text-text"
                        onClick={() =>
                          updateDraft(draft.candidate.email_message_id, (current) => ({
                            ...current,
                            internalPayables: [...current.internalPayables, { personId: "", amount: "", title: "Parte ingreso compartido" }]
                          }))
                        }
                        type="button"
                      >
                        <Plus aria-hidden="true" className="mr-1 inline h-4 w-4" />
                        Le debo parte
                      </button>
                    )}
                  </div>
                </div>
                {draft.internalReceivables.length > 0 && (
                  <div className="mt-3 space-y-2 rounded-[8px] border border-border bg-surface px-3 py-3">
                    <p className="text-xs uppercase tracking-wide text-subtle">Cuentas por cobrar internas</p>
                    {draft.internalReceivables.map((item, index) => (
                      <div className="grid gap-2 md:grid-cols-[1fr_130px_1fr_auto]" key={`${draft.candidate.email_message_id}-internal-${index}`}>
                        <select
                          className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                          onChange={(event) =>
                            updateDraft(draft.candidate.email_message_id, (current) => ({
                              ...current,
                              internalReceivables: current.internalReceivables.map((row, rowIndex) =>
                                rowIndex === index ? { ...row, personId: event.target.value } : row
                              )
                            }))
                          }
                          value={item.personId}
                        >
                          <option value="">Persona</option>
                          {people.map((person) => (
                            <option key={person.id} value={person.id}>
                              {person.name}
                            </option>
                          ))}
                        </select>
                        <input
                          className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                          inputMode="decimal"
                          onChange={(event) =>
                            updateDraft(draft.candidate.email_message_id, (current) => ({
                              ...current,
                              internalReceivables: current.internalReceivables.map((row, rowIndex) =>
                                rowIndex === index ? { ...row, amount: event.target.value } : row
                              )
                            }))
                          }
                          placeholder="Monto"
                          value={item.amount}
                        />
                        <input
                          className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                          onChange={(event) =>
                            updateDraft(draft.candidate.email_message_id, (current) => ({
                              ...current,
                              internalReceivables: current.internalReceivables.map((row, rowIndex) =>
                                rowIndex === index ? { ...row, title: event.target.value } : row
                              )
                            }))
                          }
                          placeholder="Motivo"
                          value={item.title}
                        />
                        <button
                          className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-danger"
                          onClick={() =>
                            updateDraft(draft.candidate.email_message_id, (current) => ({
                              ...current,
                              internalReceivables: current.internalReceivables.filter((_, rowIndex) => rowIndex !== index)
                            }))
                          }
                          type="button"
                        >
                          <Trash2 aria-hidden="true" className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                {draft.internalPayables.length > 0 && (
                  <div className="mt-3 space-y-2 rounded-[8px] border border-border bg-surface px-3 py-3">
                    <p className="text-xs uppercase tracking-wide text-subtle">Cuentas por pagar internas</p>
                    {draft.internalPayables.map((item, index) => (
                      <div className="grid gap-2 md:grid-cols-[1fr_130px_1fr_auto]" key={`${draft.candidate.email_message_id}-internal-payable-${index}`}>
                        <select
                          className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                          onChange={(event) =>
                            updateDraft(draft.candidate.email_message_id, (current) => ({
                              ...current,
                              internalPayables: current.internalPayables.map((row, rowIndex) =>
                                rowIndex === index ? { ...row, personId: event.target.value } : row
                              )
                            }))
                          }
                          value={item.personId}
                        >
                          <option value="">Persona</option>
                          {people.map((person) => (
                            <option key={person.id} value={person.id}>
                              {person.name}
                            </option>
                          ))}
                        </select>
                        <input
                          className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                          inputMode="decimal"
                          onChange={(event) =>
                            updateDraft(draft.candidate.email_message_id, (current) => ({
                              ...current,
                              internalPayables: current.internalPayables.map((row, rowIndex) =>
                                rowIndex === index ? { ...row, amount: event.target.value } : row
                              )
                            }))
                          }
                          placeholder="Monto"
                          value={item.amount}
                        />
                        <input
                          className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                          onChange={(event) =>
                            updateDraft(draft.candidate.email_message_id, (current) => ({
                              ...current,
                              internalPayables: current.internalPayables.map((row, rowIndex) =>
                                rowIndex === index ? { ...row, title: event.target.value } : row
                              )
                            }))
                          }
                          placeholder="Motivo"
                          value={item.title}
                        />
                        <button
                          className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-danger"
                          onClick={() =>
                            updateDraft(draft.candidate.email_message_id, (current) => ({
                              ...current,
                              internalPayables: current.internalPayables.filter((_, rowIndex) => rowIndex !== index)
                            }))
                          }
                          type="button"
                        >
                          <Trash2 aria-hidden="true" className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <div className="mt-3 space-y-2">
                  {draft.splits.map((split, index) => (
                    <div className="grid gap-2 md:grid-cols-[1fr_120px_1fr_auto]" key={`${draft.candidate.email_message_id}-${index}`}>
                      <select
                        className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                        onChange={(event) =>
                          updateDraft(draft.candidate.email_message_id, (current) => ({
                            ...current,
                            splits: current.splits.map((item, itemIndex) => (itemIndex === index ? { ...item, categoryId: event.target.value } : item))
                          }))
                        }
                        value={split.categoryId}
                      >
                        <option value="">Categoria</option>
                        {categories.map((category) => (
                          <option key={category.id} value={category.id}>
                            {category.name}
                          </option>
                        ))}
                      </select>
                      <input
                        className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                        onChange={(event) =>
                          updateDraft(draft.candidate.email_message_id, (current) => ({
                            ...current,
                            splits: current.splits.map((item, itemIndex) => (itemIndex === index ? { ...item, amount: event.target.value } : item))
                          }))
                        }
                        placeholder="Monto"
                        value={split.amount}
                      />
                      <input
                        className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text"
                        onChange={(event) =>
                          updateDraft(draft.candidate.email_message_id, (current) => ({
                            ...current,
                            splits: current.splits.map((item, itemIndex) => (itemIndex === index ? { ...item, label: event.target.value } : item))
                          }))
                        }
                        placeholder="Etiqueta"
                        value={split.label}
                      />
                      <button
                        className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-danger"
                        onClick={() =>
                          updateDraft(draft.candidate.email_message_id, (current) => ({
                            ...current,
                            splits: current.splits.filter((_, itemIndex) => itemIndex !== index)
                          }))
                        }
                        type="button"
                      >
                        <Trash2 aria-hidden="true" className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  {draft.splits.length === 0 && <p className="text-sm text-subtle">Sin desglose por ahora. Si confirmas asi, el movimiento conserva su categoria base.</p>}
                </div>
              </details>

              <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:justify-end">
                <button className="focus-ring rounded-[8px] border border-border px-4 py-2 text-sm text-muted hover:text-warning" onClick={() => archiveGmailMessage(draft.candidate.email_message_id)} type="button">
                  <X aria-hidden="true" className="mr-2 inline h-4 w-4" />
                  Archivar correo
                </button>
                <button className="focus-ring rounded-[8px] border border-border px-4 py-2 text-sm text-muted hover:text-danger" onClick={() => discardDraft(draft.candidate.email_message_id)} type="button">
                  <Trash2 aria-hidden="true" className="mr-2 inline h-4 w-4" />
                  Descartar correo
                </button>
                <button className="focus-ring rounded-[8px] bg-accent px-4 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60" disabled={draft.saving} onClick={() => confirmDraft(draft.candidate.email_message_id)} type="button">
                  <CheckCircle2 aria-hidden="true" className="mr-2 inline h-4 w-4" />
                  Confirmar importacion
                </button>
              </div>
            </article>
          );
        })}
      </section>

      {showMailbox ? (
      <section className="panel min-h-[70vh] p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-subtle">Bandeja Gmail</p>
            <h2 className="mt-1 text-xl font-semibold">Correos existentes</h2>
            <p className="mt-1 max-w-3xl text-sm text-muted">
              Lista amplia de correos ya guardados. Los errores de parser se reintentan cuando vuelves a usar Actualizar Gmail.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-[8px] border border-info/40 bg-info/10 px-2 py-1 text-info">{gmailMessageStats.parsed} candidatos</span>
            <span className="rounded-[8px] border border-warning/40 bg-warning/10 px-2 py-1 text-warning">{gmailMessageStats.parseFailed} errores parser</span>
            <span className="rounded-[8px] border border-border bg-surface2 px-2 py-1 text-muted">{gmailMessageStats.discarded} ignorados</span>
            <span className="rounded-[8px] border border-accent/40 bg-accent/10 px-2 py-1 text-accent">{gmailMessageStats.confirmed} confirmados</span>
          </div>
        </div>

        <div className="mt-5 grid gap-3 xl:grid-cols-2">
          {gmailMessages.length === 0 ? (
            <p className="rounded-[8px] border border-border bg-surface2 px-4 py-5 text-sm text-muted">
              Aun no hay correos guardados. Usa Actualizar Gmail para traer los primeros mensajes.
            </p>
          ) : (
            gmailMessages.map((message) => (
              <article className="rounded-[8px] border border-border bg-surface2 px-4 py-4" key={message.id}>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="line-clamp-2 text-base font-semibold text-text">{message.subject}</p>
                    <p className="mt-1 truncate text-sm text-subtle">
                      {message.sender_name || message.sender_email || "Remitente desconocido"} · {formatDateLabel(message.received_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className={`inline-flex w-fit rounded-[8px] border px-2 py-1 text-xs ${gmailMessageStatusClass(message.parse_status)}`}>
                      {gmailMessageStatusLabel(message.parse_status)}
                    </span>
                    <button
                      aria-label="Archivar correo"
                      className="focus-ring rounded-[8px] border border-border p-1.5 text-muted hover:text-warning"
                      onClick={() => archiveGmailMessage(message.id)}
                      type="button"
                    >
                      <X aria-hidden="true" className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <GmailMessagePreviewTabs message={message} />
              </article>
            ))
          )}
        </div>
      </section>
      ) : null}
    </div>
  );
}
