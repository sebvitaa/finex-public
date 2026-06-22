import type { CategorySpend, DailySpend, Transaction } from "../types";

export const demoMetrics = [
  {
    label: "Gasto del mes",
    value: 427_850,
    delta: "+12,4% vs mes anterior",
    tone: "danger"
  },
  {
    label: "Gasto de hoy",
    value: 18_430,
    delta: "3 movimientos",
    tone: "info"
  },
  {
    label: "Promedio diario",
    value: 15_846,
    delta: "Dentro del ritmo esperado",
    tone: "accent"
  },
  {
    label: "Por revisar",
    value: 7,
    delta: "Baja confianza",
    tone: "warning",
    format: "number"
  }
] as const;

export const dailySpend: DailySpend[] = [
  { day: "20 may", amount: 12990 },
  { day: "21 may", amount: 35400 },
  { day: "22 may", amount: 8430 },
  { day: "23 may", amount: 44590 },
  { day: "24 may", amount: 18800 },
  { day: "25 may", amount: 62990 },
  { day: "26 may", amount: 23100 },
  { day: "27 may", amount: 18430 }
];

export const categorySpend: CategorySpend[] = [
  { name: "Comida", amount: 126_540, color: "#22C55E" },
  { name: "Transporte", amount: 82_300, color: "#38BDF8" },
  { name: "Suscripciones", amount: 54_990, color: "#EC4899" },
  { name: "Supermercado", amount: 48_650, color: "#A78BFA" },
  { name: "Ocio", amount: 42_870, color: "#F59E0B" }
];

export const recentTransactions: Transaction[] = [
  {
    id: 1,
    occurredAt: "2026-05-27T13:20:00-04:00",
    merchant: "Rappi",
    description: "Almuerzo",
    amount: 18430,
    currency: "CLP",
    category: "Comida",
    categoryColor: "#22C55E",
    source: "demo",
    status: "classified",
    confidence: 0.94
  },
  {
    id: 2,
    occurredAt: "2026-05-26T21:10:00-04:00",
    merchant: "Uber Trip",
    description: "Traslado nocturno",
    amount: 12990,
    currency: "CLP",
    category: "Transporte",
    categoryColor: "#38BDF8",
    source: "gmail",
    status: "classified",
    confidence: 0.91
  },
  {
    id: 3,
    occurredAt: "2026-05-26T09:35:00-04:00",
    merchant: "Spotify",
    description: "Plan mensual",
    amount: 4550,
    currency: "CLP",
    category: "Suscripciones",
    categoryColor: "#EC4899",
    source: "gmail",
    status: "classified",
    confidence: 0.98
  },
  {
    id: 4,
    occurredAt: "2026-05-25T18:42:00-04:00",
    merchant: "Mercado Pago",
    description: "Compra online",
    amount: 24990,
    currency: "CLP",
    category: "Por revisar",
    categoryColor: "#F59E0B",
    source: "demo",
    status: "needs_review",
    confidence: 0.42
  }
];
