export function formatCurrency(amount: number, currency = "CLP") {
  const fractionDigits = currency === "USD" ? 2 : 0;
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits
  }).format(amount);
}

export function parseCurrencyInput(value: string, currency = "CLP") {
  if (currency === "USD") {
    const cleaned = value.replace(/[^\d.,]/g, "");
    const decimalIndex = Math.max(cleaned.lastIndexOf("."), cleaned.lastIndexOf(","));
    if (decimalIndex === -1) return cleaned.replace(/\D/g, "");
    const integerPart = cleaned.slice(0, decimalIndex).replace(/\D/g, "") || "0";
    const decimalPart = cleaned.slice(decimalIndex + 1).replace(/\D/g, "").slice(0, 2);
    return decimalPart ? `${integerPart}.${decimalPart}` : integerPart;
  }
  return value.replace(/\D/g, "");
}

export function normalizeMoneyInput(value: string | number | null | undefined, currency = "CLP") {
  if (value === null || value === undefined || value === "") return "";
  const numberValue = typeof value === "number" ? value : Number(value);
  if (Number.isFinite(numberValue)) return currency === "USD" ? numberValue.toFixed(2).replace(/\.00$/, "") : String(Math.round(numberValue));
  return parseCurrencyInput(String(value), currency);
}

export function formatCurrencyInput(value: string | number | null | undefined, currency = "CLP") {
  const normalized = normalizeMoneyInput(value, currency);
  if (!normalized) return "";
  return formatCurrency(Number(normalized), currency);
}

export function formatCompactCurrency(amount: number) {
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    notation: "compact",
    maximumFractionDigits: 0
  }).format(amount);
}

export function formatDateLabel(value: string) {
  const date = new Date(value);
  return new Intl.DateTimeFormat("es-CL", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

const financialAccountTypeLabels: Record<string, string> = {
  checking: "Cuenta corriente",
  savings: "Cuenta de ahorro",
  debit_card: "Tarjeta de débito",
  credit_card: "Tarjeta de crédito",
  cash: "Efectivo",
  wallet: "Billetera",
  unknown: "Sin tipo"
};

const investmentAccountTypeLabels: Record<string, string> = {
  brokerage: "Broker",
  mutual_fund: "Fondo mutuo",
  pension: "Pensión",
  crypto: "Crypto",
  savings: "Cuenta de ahorro",
  other: "Otra inversión"
};

export function formatFinancialAccountType(type: string | null | undefined) {
  if (!type) return "Sin tipo";
  return financialAccountTypeLabels[type] ?? type;
}

export function formatInvestmentAccountType(type: string | null | undefined) {
  if (!type) return "Sin tipo";
  return investmentAccountTypeLabels[type] ?? type;
}
