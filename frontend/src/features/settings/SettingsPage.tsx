import { Archive, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { GmailMessagePreviewTabs } from "../../components/GmailMessagePreviewTabs";
import { accountTone, ColorCard } from "../../components/ui/ColorCard";
import { api } from "../../lib/api";
import {
  formatCurrency,
  formatCurrencyInput,
  formatDateLabel,
  formatFinancialAccountType,
  formatInvestmentAccountType,
  parseCurrencyInput
} from "../../lib/format";
import type { Category, ClassificationRule, CurrencyCode, FinancialAccount, GmailMessage, InvestmentAccount, Person, RuleSuggestion, RuleTestResponse, TransactionType } from "../../types";

function statusLabel(status: string) {
  if (status === "parsed") return "Candidato";
  if (status === "confirmed") return "Confirmado";
  if (status === "discarded") return "Ignorado";
  if (status === "parse_failed") return "Error parser";
  return status;
}

const ruleFields: Array<{ value: ClassificationRule["field"]; label: string }> = [
  { value: "source_text", label: "Todo el texto" },
  { value: "sender_email", label: "Remitente" },
  { value: "subject", label: "Asunto" },
  { value: "merchant_name", label: "Comercio" },
  { value: "counterparty", label: "Contraparte" },
  { value: "detected_account_institution", label: "Banco" },
  { value: "detected_account_last_four", label: "Ultimos 4" },
  { value: "item_text", label: "Texto item" }
];

const transactionTypes: Array<{ value: TransactionType | ""; label: string }> = [
  { value: "", label: "Sin tipo" },
  { value: "expense", label: "Gasto" },
  { value: "income", label: "Ingreso" },
  { value: "transfer_out", label: "Transferencia enviada" },
  { value: "transfer_in", label: "Transferencia recibida" },
  { value: "internal_transfer", label: "Traspaso entre mis cuentas" },
  { value: "receivable_payment", label: "Pago cuenta por cobrar" },
  { value: "payable_payment", label: "Pago cuenta por pagar" },
  { value: "investment", label: "Inversion" },
  { value: "disinvestment", label: "Desinversion" },
  { value: "subscription", label: "Suscripcion" },
  { value: "refund", label: "Devolucion" }
];
const currencyOptions: CurrencyCode[] = ["CLP", "USD"];
const cardArtOptions = ["white", "red", "green", "black", "blue"];

type SettingsPageMode = "accounts" | "settings";

type SettingsPageProps = {
  mode?: SettingsPageMode;
};

type PersonDraft = {
  name: string;
  alias: string;
  email: string;
  phone: string;
  notes: string;
};

type CategoryDraft = {
  name: string;
  kind: Category["kind"];
  color: string;
};

function personDraft(person: Person): PersonDraft {
  return {
    name: person.name,
    alias: person.alias ?? "",
    email: person.email ?? "",
    phone: person.phone ?? "",
    notes: person.notes ?? ""
  };
}

function categoryDraft(category: Category): CategoryDraft {
  return {
    name: category.name,
    kind: category.kind,
    color: category.color
  };
}

export function SettingsPage({ mode = "settings" }: SettingsPageProps) {
  const showAccounts = mode === "accounts";
  const showConfiguration = mode === "settings";
  const [archivedMessages, setArchivedMessages] = useState<GmailMessage[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [rules, setRules] = useState<ClassificationRule[]>([]);
  const [ruleSuggestions, setRuleSuggestions] = useState<RuleSuggestion[]>([]);
  const [financialAccounts, setFinancialAccounts] = useState<FinancialAccount[]>([]);
  const [investmentAccounts, setInvestmentAccounts] = useState<InvestmentAccount[]>([]);
  const [ruleForm, setRuleForm] = useState({
    name: "",
    field: "source_text" as ClassificationRule["field"],
    operator: "contains" as ClassificationRule["operator"],
    pattern: "",
    categoryId: "",
    transactionType: "" as TransactionType | "",
    financialAccountId: "",
    investmentAccountId: "",
    priority: "100",
    confidence: "0.75"
  });
  const [ruleTestText, setRuleTestText] = useState("Cargo aprobado Spotify $4.550");
  const [ruleTestResult, setRuleTestResult] = useState<RuleTestResponse | null>(null);
  const [financialForm, setFinancialForm] = useState({
    name: "",
    institution: "",
    accountType: "checking" as FinancialAccount["account_type"],
    lastFour: "",
    currency: "CLP" as CurrencyCode,
    openingBalance: "0",
    creditLimitAmount: "",
    billingCycleDay: "",
    paymentDueDay: "",
    cardArtVariant: "black"
  });
  const [snapshotDrafts, setSnapshotDrafts] = useState<Record<number, string>>({});
  const [investmentForm, setInvestmentForm] = useState({
    name: "",
    institution: "",
    accountType: "mutual_fund" as InvestmentAccount["account_type"],
    currentValue: "0"
  });
  const [personForm, setPersonForm] = useState<PersonDraft>({ name: "", alias: "", email: "", phone: "", notes: "" });
  const [personDrafts, setPersonDrafts] = useState<Record<number, PersonDraft>>({});
  const [categoryForm, setCategoryForm] = useState<CategoryDraft>({ name: "", kind: "expense", color: "#71717A" });
  const [categoryDrafts, setCategoryDrafts] = useState<Record<number, CategoryDraft>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadArchivedMessages = useCallback(async () => {
    const [messages, categoryData, peopleData, ruleData, suggestionData, financialAccountData, investmentAccountData] = await Promise.all([
      api.gmailMessages(50, { archived_only: true, visible_only: false }),
      api.categories(),
      api.people(),
      api.rules(),
      api.ruleSuggestions(),
      api.financialAccounts({ active_only: true }),
      api.investmentAccounts({ active_only: true })
    ]);
    setArchivedMessages(messages);
    setCategories(categoryData);
    setPeople(peopleData);
    setRules(ruleData);
    setRuleSuggestions(suggestionData);
    setFinancialAccounts(financialAccountData);
    setInvestmentAccounts(investmentAccountData);
    setPersonDrafts(Object.fromEntries(peopleData.map((person) => [person.id, personDraft(person)])));
    setCategoryDrafts(Object.fromEntries(categoryData.map((category) => [category.id, categoryDraft(category)])));
  }, []);

  useEffect(() => {
    let ignore = false;
    setIsLoading(true);
    loadArchivedMessages()
      .then(() => {
        if (!ignore) setError(null);
      })
      .catch(() => {
        if (!ignore) setError("No pude cargar la configuracion.");
      })
      .finally(() => {
        if (!ignore) setIsLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, [loadArchivedMessages]);

  const stats = useMemo(
    () =>
      archivedMessages.reduce(
        (current, message) => ({
          ...current,
          [message.parse_status]: (current[message.parse_status] ?? 0) + 1
        }),
        {} as Record<string, number>
      ),
    [archivedMessages]
  );
  const customCategories = useMemo(() => categories.filter((category) => !category.is_system), [categories]);
  const systemCategories = useMemo(() => categories.filter((category) => category.is_system), [categories]);

  async function restoreMessage(messageId: number) {
    try {
      await api.gmailSetMessageVisibility(messageId, true);
      setArchivedMessages((current) => current.filter((message) => message.id !== messageId));
      setFeedback("Correo restaurado. Volvera a aparecer en Importar.");
      setError(null);
    } catch {
      setError("No pude restaurar ese correo.");
    }
  }

  async function createFinancialAccount() {
    if (!financialForm.name.trim()) return;
    try {
      await api.createFinancialAccount({
        name: financialForm.name.trim(),
        institution: financialForm.institution || null,
        account_type: financialForm.accountType,
        last_four: financialForm.lastFour || null,
        opening_balance: financialForm.openingBalance || "0",
        currency: financialForm.currency,
        credit_limit_amount: financialForm.accountType === "credit_card" && financialForm.creditLimitAmount ? financialForm.creditLimitAmount : null,
        credit_limit_currency: financialForm.accountType === "credit_card" ? financialForm.currency : null,
        billing_cycle_day: financialForm.billingCycleDay ? Number(financialForm.billingCycleDay) : null,
        payment_due_day: financialForm.paymentDueDay ? Number(financialForm.paymentDueDay) : null,
        statement_currency: financialForm.accountType === "credit_card" ? financialForm.currency : null,
        card_art_variant: financialForm.accountType === "credit_card" ? financialForm.cardArtVariant : null
      });
      setFinancialForm({
        name: "",
        institution: "",
        accountType: "checking",
        lastFour: "",
        currency: "CLP",
        openingBalance: "0",
        creditLimitAmount: "",
        billingCycleDay: "",
        paymentDueDay: "",
        cardArtVariant: "black"
      });
      await loadArchivedMessages();
      setFeedback("Cuenta financiera creada.");
      setError(null);
    } catch {
      setError("No pude crear esa cuenta financiera.");
    }
  }

  async function createSnapshot(accountId: number) {
    const balance = snapshotDrafts[accountId];
    if (!balance) return;
    try {
      await api.createFinancialAccountSnapshot(accountId, {
        captured_at: new Date().toISOString(),
        balance,
        currency: financialAccounts.find((account) => account.id === accountId)?.currency ?? "CLP",
        source: "manual"
      });
      setSnapshotDrafts((current) => ({ ...current, [accountId]: "" }));
      setFeedback("Snapshot de saldo guardado.");
      setError(null);
    } catch {
      setError("No pude guardar ese saldo.");
    }
  }

  async function createInvestmentAccount() {
    if (!investmentForm.name.trim()) return;
    try {
      await api.createInvestmentAccount({
        name: investmentForm.name.trim(),
        institution: investmentForm.institution || null,
        account_type: investmentForm.accountType,
        current_value: investmentForm.currentValue || "0",
        currency: "CLP"
      });
      setInvestmentForm({ name: "", institution: "", accountType: "mutual_fund", currentValue: "0" });
      await loadArchivedMessages();
      setFeedback("Cuenta de inversion creada.");
      setError(null);
    } catch {
      setError("No pude crear esa cuenta de inversion.");
    }
  }

  async function createPerson() {
    if (!personForm.name.trim()) return;
    try {
      await api.createPerson({
        name: personForm.name.trim(),
        alias: personForm.alias || null,
        email: personForm.email || null,
        phone: personForm.phone || null,
        notes: personForm.notes || null
      });
      setPersonForm({ name: "", alias: "", email: "", phone: "", notes: "" });
      await loadArchivedMessages();
      setFeedback("Persona creada.");
      setError(null);
    } catch {
      setError("No pude crear esa persona.");
    }
  }

  async function savePerson(person: Person) {
    const draft = personDrafts[person.id];
    if (!draft?.name.trim()) return;
    try {
      await api.updatePerson(person.id, {
        name: draft.name.trim(),
        alias: draft.alias || null,
        email: draft.email || null,
        phone: draft.phone || null,
        notes: draft.notes || null
      });
      await loadArchivedMessages();
      setFeedback("Persona actualizada.");
      setError(null);
    } catch {
      setError("No pude actualizar esa persona.");
    }
  }

  async function createCategory() {
    if (!categoryForm.name.trim()) return;
    try {
      await api.createCategory({
        name: categoryForm.name.trim(),
        color: categoryForm.color,
        icon: "tag",
        kind: categoryForm.kind,
        sort_order: 260
      });
      setCategoryForm({ name: "", kind: "expense", color: "#71717A" });
      await loadArchivedMessages();
      setFeedback("Categoria creada.");
      setError(null);
    } catch {
      setError("No pude crear esa categoria.");
    }
  }

  async function saveCategory(category: Category) {
    const draft = categoryDrafts[category.id];
    if (!draft?.name.trim()) return;
    try {
      await api.updateCategory(category.id, {
        name: draft.name.trim(),
        kind: draft.kind,
        color: draft.color
      });
      await loadArchivedMessages();
      setFeedback("Categoria actualizada.");
      setError(null);
    } catch {
      setError("No pude actualizar esa categoria.");
    }
  }

  async function deleteCategory(category: Category) {
    if (category.is_system) return;
    try {
      await api.deleteCategory(category.id);
      await loadArchivedMessages();
      setFeedback("Categoria eliminada.");
      setError(null);
    } catch {
      setError("No pude eliminar esa categoria.");
    }
  }

  function rulePayloadFromForm() {
    return {
      name: ruleForm.name.trim(),
      field: ruleForm.field,
      operator: ruleForm.operator,
      pattern: ruleForm.pattern.trim(),
      category_id: ruleForm.categoryId ? Number(ruleForm.categoryId) : null,
      transaction_type: ruleForm.transactionType || null,
      financial_account_id: ruleForm.financialAccountId ? Number(ruleForm.financialAccountId) : null,
      investment_account_id: ruleForm.investmentAccountId ? Number(ruleForm.investmentAccountId) : null,
      priority: Number(ruleForm.priority || 100),
      confidence: Number(ruleForm.confidence || 0.75)
    };
  }

  async function createRule() {
    if (!ruleForm.name.trim() || !ruleForm.pattern.trim()) return;
    try {
      await api.createRule(rulePayloadFromForm());
      setRuleForm((current) => ({ ...current, name: "", pattern: "" }));
      await loadArchivedMessages();
      setFeedback("Regla creada.");
      setError(null);
    } catch {
      setError("No pude crear esa regla. Revisa que tenga al menos un destino.");
    }
  }

  async function toggleRule(rule: ClassificationRule) {
    try {
      await api.updateRule(rule.id, { is_active: !rule.is_active });
      await loadArchivedMessages();
      setFeedback(rule.is_active ? "Regla pausada." : "Regla activada.");
      setError(null);
    } catch {
      setError("No pude actualizar esa regla.");
    }
  }

  async function testRule() {
    if (!ruleTestText.trim()) return;
    try {
      const result = await api.testRule({ raw_text: ruleTestText });
      setRuleTestResult(result);
      setError(null);
    } catch {
      setError("No pude probar las reglas con ese texto.");
    }
  }

  async function createRuleFromSuggestion(suggestion: RuleSuggestion) {
    try {
      await api.createRule({
        name: `Sugerida: ${suggestion.pattern}`,
        field: suggestion.field,
        operator: "contains",
        pattern: suggestion.pattern,
        category_id: suggestion.category_id,
        transaction_type: suggestion.transaction_type,
        financial_account_id: suggestion.financial_account_id,
        investment_account_id: suggestion.investment_account_id,
        priority: 25,
        confidence: suggestion.confidence,
        created_from_correction: true,
        notes: suggestion.reason
      });
      await loadArchivedMessages();
      setFeedback("Regla sugerida creada.");
      setError(null);
    } catch {
      setError("No pude crear la regla sugerida.");
    }
  }

  return (
    <div className="space-y-4">
      {error && <div className="panel border-danger/50 px-4 py-3 text-sm text-danger">{error}</div>}
      {feedback && <div className="panel border-accent/50 px-4 py-3 text-sm text-accent">{feedback}</div>}

      {showAccounts ? (
      <section className="grid gap-4 xl:grid-cols-2">
        <div className="panel p-5">
          <h2 className="text-xl font-semibold">Tarjetas y cuentas</h2>
          <div className="mt-4 grid gap-2 md:grid-cols-2">
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFinancialForm((current) => ({ ...current, name: event.target.value }))} placeholder="Nombre" value={financialForm.name} />
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFinancialForm((current) => ({ ...current, institution: event.target.value }))} placeholder="Banco o institucion" value={financialForm.institution} />
            <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFinancialForm((current) => ({ ...current, accountType: event.target.value as FinancialAccount["account_type"] }))} value={financialForm.accountType}>
              <option value="checking">Cuenta corriente</option>
              <option value="savings">Cuenta de ahorro</option>
              <option value="debit_card">Tarjeta de débito</option>
              <option value="credit_card">Tarjeta de crédito</option>
              <option value="wallet">Billetera</option>
              <option value="cash">Efectivo</option>
              <option value="unknown">Sin tipo</option>
            </select>
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" maxLength={4} onChange={(event) => setFinancialForm((current) => ({ ...current, lastFour: event.target.value }))} placeholder="Ultimos 4" value={financialForm.lastFour} />
            <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFinancialForm((current) => ({ ...current, currency: event.target.value as CurrencyCode, openingBalance: parseCurrencyInput(current.openingBalance, event.target.value) }))} value={financialForm.currency}>
              {currencyOptions.map((currency) => <option key={currency} value={currency}>{currency}</option>)}
            </select>
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFinancialForm((current) => ({ ...current, openingBalance: parseCurrencyInput(event.target.value, current.currency) }))} placeholder="Saldo inicial" value={formatCurrencyInput(financialForm.openingBalance, financialForm.currency)} />
            {financialForm.accountType === "credit_card" ? (
              <>
                <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFinancialForm((current) => ({ ...current, creditLimitAmount: parseCurrencyInput(event.target.value, current.currency) }))} placeholder="Cupo total" value={formatCurrencyInput(financialForm.creditLimitAmount, financialForm.currency)} />
                <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" inputMode="numeric" maxLength={2} onChange={(event) => setFinancialForm((current) => ({ ...current, billingCycleDay: event.target.value.replace(/\D/g, "").slice(0, 2) }))} placeholder="Dia facturacion" value={financialForm.billingCycleDay} />
                <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" inputMode="numeric" maxLength={2} onChange={(event) => setFinancialForm((current) => ({ ...current, paymentDueDay: event.target.value.replace(/\D/g, "").slice(0, 2) }))} placeholder="Dia pago" value={financialForm.paymentDueDay} />
                <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setFinancialForm((current) => ({ ...current, cardArtVariant: event.target.value }))} value={financialForm.cardArtVariant}>
                  {cardArtOptions.map((variant) => <option key={variant} value={variant}>{variant}</option>)}
                </select>
              </>
            ) : null}
            <button className="focus-ring rounded-[8px] bg-accent px-3 py-2 text-sm font-semibold text-black" onClick={createFinancialAccount} type="button">Crear cuenta</button>
          </div>
          <div className="mt-4 space-y-2">
            {financialAccounts.map((account) => (
              <ColorCard className="p-3" key={account.id} tone={accountTone(account.card_art_variant, account.account_type)}>
                <p className="font-medium text-text">{account.name}</p>
                <p className="text-xs text-subtle">
                  {account.institution ?? "Sin institucion"} · {formatFinancialAccountType(account.account_type)} · {account.currency}{account.last_four ? ` · ****${account.last_four}` : ""}
                </p>
                <p className="mt-1 text-sm text-text">
                  Saldo inicial {formatCurrency(Number(account.opening_balance), account.currency)}
                  {account.credit_limit_amount ? ` · Cupo ${formatCurrency(Number(account.credit_limit_amount), account.credit_limit_currency ?? account.currency)}` : ""}
                  {account.statement_amount ? ` · Estado ${formatCurrency(Number(account.statement_amount), account.statement_currency ?? account.currency)}` : ""}
                </p>
                <div className="mt-2 flex gap-2">
                  <input className="focus-ring min-w-0 flex-1 rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setSnapshotDrafts((current) => ({ ...current, [account.id]: parseCurrencyInput(event.target.value, account.currency) }))} placeholder="Saldo actual" value={formatCurrencyInput(snapshotDrafts[account.id] ?? "", account.currency)} />
                  <button className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-accent" onClick={() => createSnapshot(account.id)} type="button">Guardar saldo</button>
                </div>
              </ColorCard>
            ))}
          </div>
        </div>

        <div className="panel p-5">
          <h2 className="text-xl font-semibold">Cuentas de inversion</h2>
          <div className="mt-4 grid gap-2 md:grid-cols-2">
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setInvestmentForm((current) => ({ ...current, name: event.target.value }))} placeholder="Nombre" value={investmentForm.name} />
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setInvestmentForm((current) => ({ ...current, institution: event.target.value }))} placeholder="Institucion" value={investmentForm.institution} />
            <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setInvestmentForm((current) => ({ ...current, accountType: event.target.value as InvestmentAccount["account_type"] }))} value={investmentForm.accountType}>
              <option value="mutual_fund">Fondo mutuo</option>
              <option value="brokerage">Broker</option>
              <option value="pension">Pensión</option>
              <option value="crypto">Crypto</option>
              <option value="savings">Cuenta de ahorro</option>
              <option value="other">Otra inversión</option>
            </select>
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setInvestmentForm((current) => ({ ...current, currentValue: parseCurrencyInput(event.target.value) }))} placeholder="Valor actual" value={formatCurrencyInput(investmentForm.currentValue)} />
            <button className="focus-ring rounded-[8px] bg-accent px-3 py-2 text-sm font-semibold text-black md:col-span-2" onClick={createInvestmentAccount} type="button">Crear inversion</button>
          </div>
          <div className="mt-4 space-y-2">
            {investmentAccounts.map((account) => (
              <ColorCard className="p-3" key={account.id} tone="info">
                <p className="font-medium text-text">{account.name}</p>
                <p className="text-xs text-subtle">
                  {account.institution ?? "Sin institucion"} · {formatInvestmentAccountType(account.account_type)} · Valor{" "}
                  {formatCurrency(Number(account.current_value), account.currency)}
                </p>
              </ColorCard>
            ))}
          </div>
        </div>
      </section>
      ) : null}

      {showConfiguration ? (
      <section className="grid gap-4 xl:grid-cols-2">
        <div className="panel p-5">
          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-subtle">Administracion</p>
              <h2 className="mt-1 text-xl font-semibold">Personas</h2>
              <p className="mt-1 text-sm text-muted">Mantiene alumnos, deudores y contrapartes fuera del registro operativo.</p>
            </div>
            <span className="w-fit rounded-[8px] border border-border bg-surface2 px-2 py-1 text-xs text-muted">{people.length} guardadas</span>
          </div>

          <div className="mt-4 grid gap-2 md:grid-cols-2">
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setPersonForm((current) => ({ ...current, name: event.target.value }))} placeholder="Nombre" value={personForm.name} />
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setPersonForm((current) => ({ ...current, alias: event.target.value }))} placeholder="Alias" value={personForm.alias} />
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setPersonForm((current) => ({ ...current, email: event.target.value }))} placeholder="Email" value={personForm.email} />
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setPersonForm((current) => ({ ...current, phone: event.target.value }))} placeholder="Telefono" value={personForm.phone} />
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text md:col-span-2" onChange={(event) => setPersonForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Notas" value={personForm.notes} />
            <button className="focus-ring rounded-[8px] bg-accent px-3 py-2 text-sm font-semibold text-black md:col-span-2" onClick={createPerson} type="button">Crear persona</button>
          </div>

          <div className="mt-4 space-y-2">
            {people.map((person) => {
              const draft = personDrafts[person.id] ?? personDraft(person);
              return (
                <div className="rounded-[8px] border border-border bg-surface2 p-3" key={person.id}>
                  <div className="grid gap-2 md:grid-cols-[1fr_1fr_auto]">
                    <input className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setPersonDrafts((current) => ({ ...current, [person.id]: { ...draft, name: event.target.value } }))} value={draft.name} />
                    <input className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setPersonDrafts((current) => ({ ...current, [person.id]: { ...draft, alias: event.target.value } }))} placeholder="Alias" value={draft.alias} />
                    <button className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-accent" onClick={() => savePerson(person)} type="button">Guardar</button>
                  </div>
                  <div className="mt-2 grid gap-2 md:grid-cols-2">
                    <input className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setPersonDrafts((current) => ({ ...current, [person.id]: { ...draft, email: event.target.value } }))} placeholder="Email" value={draft.email} />
                    <input className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setPersonDrafts((current) => ({ ...current, [person.id]: { ...draft, phone: event.target.value } }))} placeholder="Telefono" value={draft.phone} />
                  </div>
                  <input className="focus-ring mt-2 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setPersonDrafts((current) => ({ ...current, [person.id]: { ...draft, notes: event.target.value } }))} placeholder="Notas" value={draft.notes} />
                </div>
              );
            })}
            {people.length === 0 && <p className="rounded-[8px] border border-border bg-surface2 px-4 py-5 text-sm text-muted">Aun no hay personas creadas.</p>}
          </div>
        </div>

        <div className="panel p-5">
          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-subtle">Administracion</p>
              <h2 className="mt-1 text-xl font-semibold">Categorias</h2>
              <p className="mt-1 text-sm text-muted">Crea y ajusta categorias propias; las de sistema quedan como referencia.</p>
            </div>
            <span className="w-fit rounded-[8px] border border-border bg-surface2 px-2 py-1 text-xs text-muted">{customCategories.length} propias</span>
          </div>

          <div className="mt-4 grid gap-2 md:grid-cols-[1fr_130px_64px_auto]">
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setCategoryForm((current) => ({ ...current, name: event.target.value }))} placeholder="Golosinas, Clases..." value={categoryForm.name} />
            <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setCategoryForm((current) => ({ ...current, kind: event.target.value as Category["kind"] }))} value={categoryForm.kind}>
              <option value="expense">Gasto</option>
              <option value="income">Ingreso</option>
              <option value="both">Ambas</option>
            </select>
            <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-2 py-2" onChange={(event) => setCategoryForm((current) => ({ ...current, color: event.target.value }))} type="color" value={categoryForm.color} />
            <button className="focus-ring rounded-[8px] bg-accent px-3 py-2 text-sm font-semibold text-black" onClick={createCategory} type="button">Crear</button>
          </div>

          <div className="mt-4 space-y-2">
            {customCategories.map((category) => {
              const draft = categoryDrafts[category.id] ?? categoryDraft(category);
              return (
                <div className="grid gap-2 rounded-[8px] border border-border bg-surface2 p-3 md:grid-cols-[1fr_130px_64px_auto_auto]" key={category.id}>
                  <input className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setCategoryDrafts((current) => ({ ...current, [category.id]: { ...draft, name: event.target.value } }))} value={draft.name} />
                  <select className="focus-ring rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setCategoryDrafts((current) => ({ ...current, [category.id]: { ...draft, kind: event.target.value as Category["kind"] } }))} value={draft.kind}>
                    <option value="expense">Gasto</option>
                    <option value="income">Ingreso</option>
                    <option value="both">Ambas</option>
                  </select>
                  <input className="focus-ring rounded-[8px] border border-border bg-surface px-2 py-2" onChange={(event) => setCategoryDrafts((current) => ({ ...current, [category.id]: { ...draft, color: event.target.value } }))} type="color" value={draft.color} />
                  <button className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-accent" onClick={() => saveCategory(category)} type="button">Guardar</button>
                  <button className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-danger" onClick={() => deleteCategory(category)} type="button">Eliminar</button>
                </div>
              );
            })}
            {customCategories.length === 0 && <p className="rounded-[8px] border border-border bg-surface2 px-4 py-5 text-sm text-muted">Aun no hay categorias propias.</p>}
          </div>

          <details className="mt-4 rounded-[8px] border border-border bg-surface2 p-3">
            <summary className="focus-ring cursor-pointer rounded-[8px] text-sm font-semibold text-text">
              Categorias de sistema
              <span className="ml-2 text-xs font-normal text-subtle">{systemCategories.length} base</span>
            </summary>
            <div className="mt-3 flex flex-wrap gap-2">
              {systemCategories.map((category) => (
                <span className="rounded-[8px] border border-border bg-surface px-2 py-1 text-xs text-muted" key={category.id}>
                  {category.name}
                </span>
              ))}
            </div>
          </details>
        </div>
      </section>
      ) : null}

      {showConfiguration ? (
      <section className="panel p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-subtle">Fase 9</p>
            <h2 className="mt-1 text-xl font-semibold">Reglas de clasificacion</h2>
            <p className="mt-1 max-w-3xl text-sm text-muted">
              Las reglas explican por que FinEx sugiere categoria, tipo, cuenta o inversion en correos y transacciones.
            </p>
          </div>
          <span className="rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-muted">
            {rules.filter((rule) => rule.is_active).length}/{rules.length} activas
          </span>
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_1.2fr]">
          <div className="space-y-3">
            <details className="rounded-[8px] border border-border bg-surface2 p-3">
              <summary className="focus-ring cursor-pointer rounded-[8px] text-sm font-semibold text-text">
                Crear o probar regla
                <span className="ml-2 text-xs font-normal text-subtle">opcional para afinar el clasificador</span>
              </summary>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
              <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setRuleForm((current) => ({ ...current, name: event.target.value }))} placeholder="Nombre de regla" value={ruleForm.name} />
              <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setRuleForm((current) => ({ ...current, pattern: event.target.value }))} placeholder="Patron: spotify, uber, 9876..." value={ruleForm.pattern} />
              <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setRuleForm((current) => ({ ...current, field: event.target.value as ClassificationRule["field"] }))} value={ruleForm.field}>
                {ruleFields.map((field) => <option key={field.value} value={field.value}>{field.label}</option>)}
              </select>
              <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setRuleForm((current) => ({ ...current, operator: event.target.value as ClassificationRule["operator"] }))} value={ruleForm.operator}>
                <option value="contains">Contiene</option>
                <option value="equals">Es igual</option>
                <option value="starts_with">Empieza con</option>
                <option value="regex">Regex</option>
              </select>
              <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setRuleForm((current) => ({ ...current, categoryId: event.target.value }))} value={ruleForm.categoryId}>
                <option value="">Sin categoria</option>
                {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
              </select>
              <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setRuleForm((current) => ({ ...current, transactionType: event.target.value as TransactionType | "" }))} value={ruleForm.transactionType}>
                {transactionTypes.map((type) => <option key={type.value || "none"} value={type.value}>{type.label}</option>)}
              </select>
              <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setRuleForm((current) => ({ ...current, financialAccountId: event.target.value }))} value={ruleForm.financialAccountId}>
                <option value="">Sin cuenta</option>
                {financialAccounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}
              </select>
              <select className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setRuleForm((current) => ({ ...current, investmentAccountId: event.target.value }))} value={ruleForm.investmentAccountId}>
                <option value="">Sin inversion</option>
                {investmentAccounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}
              </select>
              <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setRuleForm((current) => ({ ...current, priority: event.target.value }))} placeholder="Prioridad" value={ruleForm.priority} />
              <input className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text" onChange={(event) => setRuleForm((current) => ({ ...current, confidence: event.target.value }))} placeholder="Confianza 0-1" value={ruleForm.confidence} />
            </div>
            <button className="focus-ring w-full rounded-[8px] bg-accent px-4 py-2 text-sm font-semibold text-black" onClick={createRule} type="button">Crear regla</button>

            <div className="mt-3 rounded-[8px] border border-border bg-surface p-3">
              <p className="text-sm font-medium text-text">Probar reglas</p>
              <textarea className="focus-ring mt-2 min-h-24 w-full rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-text" onChange={(event) => setRuleTestText(event.target.value)} value={ruleTestText} />
              <button className="focus-ring mt-2 rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-accent" onClick={testRule} type="button">Probar texto</button>
              {ruleTestResult && (
                <div className="mt-3 rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-muted">
                  <p>Categoria: {ruleTestResult.category_name ?? "Sin match"} · Tipo: {ruleTestResult.transaction_type ?? "Sin tipo"}</p>
                  <p>Cuenta: {ruleTestResult.financial_account_name ?? "Sin cuenta"} · Confianza: {ruleTestResult.confidence ?? 0}</p>
                  {ruleTestResult.reason && <p className="mt-1 text-xs text-subtle">{ruleTestResult.reason}</p>}
                </div>
              )}
            </div>
            </details>
          </div>

          <div className="space-y-3">
            {ruleSuggestions.length > 0 && (
              <div className="rounded-[8px] border border-warning/40 bg-warning/10 p-3">
                <p className="text-sm font-medium text-warning">Sugerencias por correcciones</p>
                <div className="mt-2 space-y-2">
                  {ruleSuggestions.slice(0, 4).map((suggestion) => (
                    <div className="flex flex-col gap-2 rounded-[8px] border border-border bg-surface px-3 py-2 text-sm md:flex-row md:items-center md:justify-between" key={`${suggestion.field}:${suggestion.pattern}`}>
                      <span className="text-muted">{suggestion.pattern} → {suggestion.category_name ?? suggestion.transaction_type ?? suggestion.financial_account_name ?? "regla"} ({suggestion.count})</span>
                      <button className="focus-ring rounded-[8px] border border-border px-3 py-1 text-xs text-muted hover:text-accent" onClick={() => createRuleFromSuggestion(suggestion)} type="button">Crear</button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="max-h-[520px] space-y-2 overflow-auto pr-1">
              {rules.map((rule) => (
                <div className="rounded-[8px] border border-border bg-surface2 p-3 text-sm" key={rule.id}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-text">{rule.name}</p>
                      <p className="mt-1 text-xs text-subtle">{rule.field} {rule.operator} "{rule.pattern}" · prioridad {rule.priority} · confianza {rule.confidence}</p>
                    </div>
                    <button className="focus-ring rounded-[8px] border border-border px-3 py-1 text-xs text-muted hover:text-accent" onClick={() => toggleRule(rule)} type="button">
                      {rule.is_active ? "Pausar" : "Activar"}
                    </button>
                  </div>
                  <p className="mt-2 text-xs text-muted">
                    {rule.category_name ?? "Sin categoria"} · {rule.transaction_type ?? "Sin tipo"} · {rule.financial_account_name ?? "Sin cuenta"} · {rule.investment_account_name ?? "Sin inversion"}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
      ) : null}

      {showConfiguration ? (
      <section className="panel p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-subtle">Privacidad local</p>
            <h2 className="mt-1 text-xl font-semibold">Correos archivados</h2>
            <p className="mt-1 max-w-3xl text-sm text-muted">
              Estos correos siguen guardados en FinEx, pero no aparecen en Importar ni como candidatos. Gmail no se modifica.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-[8px] border border-border bg-surface2 px-2 py-1 text-muted">
              {archivedMessages.length} archivados
            </span>
            {Object.entries(stats).map(([status, count]) => (
              <span className="rounded-[8px] border border-border bg-surface2 px-2 py-1 text-subtle" key={status}>
                {statusLabel(status)}: {count}
              </span>
            ))}
          </div>
        </div>

        <div className="mt-5 grid gap-3 xl:grid-cols-2">
          {isLoading ? (
            <p className="rounded-[8px] border border-border bg-surface2 px-4 py-5 text-sm text-muted">Cargando archivados...</p>
          ) : archivedMessages.length === 0 ? (
            <div className="rounded-[8px] border border-border bg-surface2 px-4 py-5 text-sm text-muted">
              <Archive aria-hidden="true" className="mb-2 h-5 w-5 text-subtle" />
              No hay correos archivados por ahora.
            </div>
          ) : (
            archivedMessages.map((message) => (
              <article className="rounded-[8px] border border-border bg-surface2 p-4" key={message.id}>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="line-clamp-2 font-semibold text-text">{message.subject}</p>
                    <p className="mt-1 truncate text-sm text-subtle">
                      {message.sender_name || message.sender_email || "Remitente desconocido"} · {formatDateLabel(message.received_at)}
                    </p>
                  </div>
                  <button
                    className="focus-ring w-fit rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-accent"
                    onClick={() => restoreMessage(message.id)}
                    type="button"
                  >
                    <RotateCcw aria-hidden="true" className="mr-2 inline h-4 w-4" />
                    Restaurar
                  </button>
                </div>
                <GmailMessagePreviewTabs message={message} />
                <p className="mt-3 text-xs text-subtle">Estado original: {statusLabel(message.parse_status)}</p>
              </article>
            ))
          )}
        </div>
      </section>
      ) : null}
    </div>
  );
}
