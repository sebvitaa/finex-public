import { CalendarClock, Download, HandCoins, ReceiptText, Scale, Wallet } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CategoryBadge } from "../../components/ui/CategoryBadge";
import { accountTone, ColorCard } from "../../components/ui/ColorCard";
import { DataTable, type DataTableColumn } from "../../components/ui/DataTable";
import { EmptyState } from "../../components/ui/EmptyState";
import { MetricCard } from "../../components/ui/MetricCard";
import { Modal } from "../../components/ui/Modal";
import { Reveal } from "../../components/ui/Reveal";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { api } from "../../lib/api";
import { formatCompactCurrency, formatCurrency, formatDateLabel, formatFinancialAccountType, formatInvestmentAccountType } from "../../lib/format";
import type {
  DashboardBudgetProgress,
  DashboardCategoryTotal,
  DashboardInsight,
  DashboardObligationPersonTotal,
  DashboardOverview,
  DashboardPersonTotal,
  DashboardTransaction
} from "../../types";

const metricIcons = [
  <Wallet aria-hidden="true" className="h-4 w-4" />,
  <Scale aria-hidden="true" className="h-4 w-4" />,
  <ReceiptText aria-hidden="true" className="h-4 w-4" />,
  <HandCoins aria-hidden="true" className="h-4 w-4" />,
  <CalendarClock aria-hidden="true" className="h-4 w-4" />
];

const monthOptions = [
  { value: "", label: "Mes actual" },
  { value: "1", label: "Enero" },
  { value: "2", label: "Febrero" },
  { value: "3", label: "Marzo" },
  { value: "4", label: "Abril" },
  { value: "5", label: "Mayo" },
  { value: "6", label: "Junio" },
  { value: "7", label: "Julio" },
  { value: "8", label: "Agosto" },
  { value: "9", label: "Septiembre" },
  { value: "10", label: "Octubre" },
  { value: "11", label: "Noviembre" },
  { value: "12", label: "Diciembre" }
];

function toNumber(value: string | number | null | undefined) {
  return Number(value ?? 0);
}

function loadSavedDashboardFilters() {
  if (import.meta.env.MODE === "test") return { year: "", month: "" };
  if (typeof window === "undefined") return { year: "", month: "" };
  try {
    const saved = window.localStorage.getItem("finex.dashboard.filters");
    if (!saved) return { year: "", month: "" };
    const parsed = JSON.parse(saved) as { year?: string; month?: string };
    return { year: parsed.year ?? "", month: parsed.month ?? "" };
  } catch {
    return { year: "", month: "" };
  }
}

function CategoryRanking({ emptyBody, items, title }: { emptyBody: string; items: DashboardCategoryTotal[]; title: string }) {
  const max = Math.max(...items.map((item) => toNumber(item.amount)), 1);

  return (
    <div className="panel p-4">
      <h2 className="text-base font-semibold">{title}</h2>
      {items.length === 0 ? (
        <EmptyState body={emptyBody} title="Sin datos aun" />
      ) : (
        <div className="mt-4 space-y-4">
          {items.map((item) => {
            const amount = toNumber(item.amount);
            return (
              <div className="space-y-2" key={`${item.category_id}-${item.name}`}>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <CategoryBadge color={item.color} name={item.name} />
                  <span className="font-medium text-text">{formatCurrency(amount)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-surface2">
                  <div
                    className="h-full rounded-full"
                    style={{
                      backgroundColor: item.color,
                      width: `${Math.max(8, (amount / max) * 100)}%`
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function formatPercent(value: string | number | null | undefined) {
  if (value === null || value === undefined) return "sin base";
  return `${Number(value).toFixed(1)}%`;
}

function DeltaLine({ label, percent, positiveGood = false, value }: { label: string; percent?: string | null; positiveGood?: boolean; value: string | number }) {
  const numericValue = toNumber(value);
  const tone = numericValue > 0 ? (positiveGood ? "text-accent" : "text-warning") : numericValue < 0 ? (positiveGood ? "text-warning" : "text-accent") : "text-muted";
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border/70 pb-2 text-sm">
      <span className="text-muted">{label}</span>
      <span className={`font-medium ${tone}`}>
        {numericValue > 0 ? "+" : ""}
        {formatCurrency(numericValue)} · {formatPercent(percent)}
      </span>
    </div>
  );
}

function InsightList({ insights }: { insights: DashboardInsight[] }) {
  const toneBySeverity: Record<string, string> = {
    success: "border-accent/40 bg-accent/5 text-accent",
    warning: "border-warning/40 bg-warning/5 text-warning",
    info: "border-info/40 bg-info/5 text-info"
  };

  return (
    <div className="panel p-4">
      <h2 className="text-base font-semibold">Insights accionables</h2>
      <p className="mt-1 text-sm text-muted">Alertas simples sobre ritmo, comercios y categorias.</p>
      <div className="mt-4 space-y-3">
        {insights.length === 0 ? (
          <EmptyState body="Cuando haya movimientos suficientes, FinEx marcara cambios relevantes." title="Sin alertas aun" />
        ) : (
          insights.map((insight) => (
            <div className={`rounded-[8px] border px-3 py-2 ${toneBySeverity[insight.severity] ?? toneBySeverity.info}`} key={`${insight.kind}-${insight.title}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-text">{insight.title}</p>
                  <p className="mt-1 text-xs text-muted">{insight.detail}</p>
                </div>
                {insight.amount ? <span className="shrink-0 text-sm font-semibold text-text">{formatCurrency(toNumber(insight.amount))}</span> : null}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function DailyHeatmap({ overview }: { overview: DashboardOverview | null }) {
  const points = overview?.daily_heatmap ?? [];
  return (
    <div className="panel p-4">
      <h2 className="text-base font-semibold">Heatmap diario</h2>
      <p className="mt-1 text-sm text-muted">Cada cuadro es un dia del periodo.</p>
      {points.length === 0 ? (
        <EmptyState body="Aparecera cuando exista gasto diario en el periodo." title="Sin dias" />
      ) : (
        <div className="mt-4 grid grid-cols-7 gap-1">
          {points.map((point) => {
            const alpha = point.intensity === 0 ? 0.08 : 0.18 + point.intensity * 0.72;
            return (
              <div
                className="aspect-square rounded-[6px] border border-border/70 p-1 text-[10px] text-subtle"
                key={point.date}
                style={{ backgroundColor: `rgba(239, 68, 68, ${alpha})` }}
                title={`${point.date}: ${formatCurrency(toNumber(point.expense))}`}
              >
                {point.day}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function BudgetPanel({ budgets }: { budgets: DashboardBudgetProgress[] }) {
  return (
    <div className="panel p-4">
      <h2 className="text-base font-semibold">Presupuestos base</h2>
      <p className="mt-1 text-sm text-muted">Supermercado, golosinas, aseo y otros focos del mes.</p>
      <div className="mt-4 space-y-4">
        {budgets.length === 0 ? (
          <EmptyState body="No encontre categorias presupuestadas en la base local." title="Sin presupuestos" />
        ) : (
          budgets.map((budget) => {
            const usage = Math.max(0, Math.min(100, toNumber(budget.usage_percent)));
            const tone = budget.status === "over" ? "text-danger" : budget.status === "watch" ? "text-warning" : "text-accent";
            return (
              <div className="space-y-2" key={budget.name}>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <CategoryBadge color={budget.color} name={budget.name} />
                  <span className={`font-medium ${tone}`}>{formatPercent(budget.usage_percent)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-surface2">
                  <div className="h-full rounded-full" style={{ backgroundColor: budget.color, width: `${Math.max(4, usage)}%` }} />
                </div>
                <p className="text-xs text-subtle">
                  {formatCurrency(toNumber(budget.spent_amount))} de {formatCurrency(toNumber(budget.budget_amount))} · queda{" "}
                  {formatCurrency(toNumber(budget.remaining_amount))}
                </p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function PersonIncomeList({ people }: { people: DashboardPersonTotal[] }) {
  return (
    <div className="panel p-4">
      <h2 className="text-base font-semibold">Ingresos por clases</h2>
      <p className="mt-1 text-sm text-muted">Agrupado por alumno/persona cuando esta enlazado.</p>
      <div className="mt-4 space-y-3">
        {people.length === 0 ? (
          <EmptyState body="Registra ingresos de clases con persona para ver este ranking." title="Sin clases" />
        ) : (
          people.map((person) => (
            <div className="flex items-center justify-between gap-3 border-b border-border/70 pb-3 text-sm" key={`${person.person_id}-${person.person_name}`}>
              <div className="min-w-0">
                <p className="truncate font-medium text-text">{person.person_name}</p>
                <p className="text-xs text-subtle">{person.count} ingresos</p>
              </div>
              <span className="font-semibold text-accent">{formatCurrency(toNumber(person.amount))}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function ObligationList({ emptyBody, items, title }: { emptyBody: string; items: DashboardObligationPersonTotal[]; title: string }) {
  return (
    <div className="panel p-4">
      <h2 className="text-base font-semibold">{title}</h2>
      <div className="mt-4 space-y-3">
        {items.length === 0 ? (
          <EmptyState body={emptyBody} title="Sin pendientes" />
        ) : (
          items.map((item) => (
            <div className="flex items-start justify-between gap-3 border-b border-border/70 pb-3 text-sm" key={`${item.person_id}-${item.person_name}`}>
              <div className="min-w-0">
                <p className="truncate font-medium text-text">{item.person_name}</p>
                <p className="text-xs text-subtle">
                  {item.count} pendientes{item.overdue_count ? ` · ${item.overdue_count} vencidas` : ""}
                </p>
              </div>
              <span className="font-semibold text-warning">{formatCurrency(toNumber(item.amount))}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export function DashboardPage() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [periodFilter, setPeriodFilter] = useState(loadSavedDashboardFilters);

  async function loadDashboard() {
    setIsLoading(true);
    try {
      const data = await api.dashboardOverview({
        year: periodFilter.year ? Number(periodFilter.year) : "",
        month: periodFilter.month ? Number(periodFilter.month) : ""
      });
      setOverview(data);
      setError(null);
    } catch {
      setError("No pude cargar el dashboard real. Revisa que el backend este arriba.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, [periodFilter.month, periodFilter.year]);

  useEffect(() => {
    if (import.meta.env.MODE === "test") return;
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem("finex.dashboard.filters", JSON.stringify(periodFilter));
    } catch {
      return;
    }
  }, [periodFilter]);

  async function exportCsv() {
    setIsExporting(true);
    try {
      const blob = await api.dashboardExportCsv({
        year: periodFilter.year ? Number(periodFilter.year) : "",
        month: periodFilter.month ? Number(periodFilter.month) : ""
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `finex-dashboard-${overview?.period.label.replace("/", "-") ?? "actual"}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setError(null);
    } catch {
      setError("No pude exportar el CSV. Revisa que el backend este arriba.");
    } finally {
      setIsExporting(false);
    }
  }

  const metrics = useMemo(() => {
    const data = overview?.metrics;
    return [
      {
        label: "Liquidez",
        value: toNumber(data?.liquid_balance),
        delta: "Cuentas y efectivo; excluye credito",
        tone: "info" as const
      },
      {
        label: "Inversiones",
        value: toNumber(data?.investment_balance),
        delta: "Patrimonio invertido separado",
        tone: "accent" as const
      },
      {
        label: "Gasto del mes",
        value: toNumber(data?.month_expense),
        delta: "Suma real de gastos del periodo",
        tone: "danger" as const
      },
      {
        label: "Ingresos del mes",
        value: toNumber(data?.month_income),
        delta: "Ingresos separados de gastos",
        tone: "accent" as const
      },
      {
        label: "Balance real",
        value: toNumber(data?.net_balance),
        delta: "Ingresos menos gastos del periodo",
        tone: toNumber(data?.net_balance) >= 0 ? ("accent" as const) : ("warning" as const)
      }
    ];
  }, [overview]);

  const chartData = useMemo(
    () =>
      (overview?.daily ?? []).map((point) => ({
        label: point.label,
        expense: toNumber(point.expense),
        income: toNumber(point.income),
        balance: toNumber(point.balance)
      })),
    [overview]
  );

  const columns = useMemo<DataTableColumn<DashboardTransaction>[]>(
    () => [
      {
        key: "merchant",
        header: "Movimiento",
        cell: (row) => (
          <div className="min-w-0">
            <p className="truncate font-medium text-text">{row.merchant_name ?? row.counterparty ?? "Movimiento"}</p>
            <p className="truncate text-xs text-subtle">{row.description ?? row.transaction_type}</p>
          </div>
        )
      },
      {
        key: "date",
        header: "Fecha",
        cell: (row) => formatDateLabel(row.occurred_at)
      },
      {
        key: "category",
        header: "Categoria",
        cell: (row) => <CategoryBadge color={row.category_color ?? "#71717A"} name={row.category_name ?? "Sin categoria"} />
      },
      {
        key: "status",
        header: "Estado",
        cell: (row) => <StatusBadge status={row.status} />
      },
      {
        key: "amount",
        header: "Monto",
        align: "right",
        cell: (row) => <span className="font-medium text-text">{formatCurrency(toNumber(row.amount), row.currency)}</span>
      }
    ],
    []
  );

  return (
    <div className="space-y-4">
      {error ? <div className="panel border-danger/50 px-4 py-3 text-sm text-danger">{error}</div> : null}

      <Reveal>
        <section className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(190px,1fr))]">
          {metrics.map((metric, index) => (
            <MetricCard icon={metricIcons[index]} key={metric.label} {...metric} />
          ))}
        </section>
      </Reveal>

      <section className="grid gap-3 md:grid-cols-3">
        <ColorCard tone="info" className="flex items-center justify-between gap-3 p-3 text-sm">
          <span className="text-muted">Proyeccion mensual</span>
          <span className="font-semibold text-info tabular-nums">{formatCurrency(toNumber(overview?.metrics.projected_month_expense))}</span>
        </ColorCard>
        <ColorCard tone="neutral" className="flex items-center justify-between gap-3 p-3 text-sm">
          <span className="text-muted">Promedio diario</span>
          <span className="font-semibold text-text tabular-nums">{formatCurrency(toNumber(overview?.metrics.daily_average_expense))}</span>
        </ColorCard>
        <ColorCard tone="warning" className="flex items-center justify-between gap-3 p-3 text-sm">
          <span className="text-muted">Por revisar</span>
          <span className="font-semibold text-warning tabular-nums">{overview?.metrics.review_count ?? 0}</span>
        </ColorCard>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.5fr_0.9fr]">
        <div className="panel min-h-[320px] p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-base font-semibold">Gasto e ingreso acumulado</h2>
              <p className="text-sm text-muted">
                {isLoading ? "Cargando datos reales..." : `Periodo ${overview?.period.label ?? "actual"}. El balance no mezcla cuentas por cobrar pendientes.`}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <input
                className="focus-ring w-24 rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                max="2100"
                min="2000"
                onChange={(event) => setPeriodFilter((current) => ({ ...current, year: event.target.value }))}
                placeholder="Ano"
                type="number"
                value={periodFilter.year}
              />
              <select
                className="focus-ring rounded-[8px] border border-border bg-surface2 px-3 py-2 text-sm text-text"
                onChange={(event) => setPeriodFilter((current) => ({ ...current, month: event.target.value }))}
                value={periodFilter.month}
              >
                {monthOptions.map((month) => (
                  <option key={month.value || "current"} value={month.value}>
                    {month.label}
                  </option>
                ))}
              </select>
              <button className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-text" onClick={loadDashboard} type="button">
                Actualizar
              </button>
              <button
                className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-text"
                disabled={isExporting}
                onClick={exportCsv}
                type="button"
              >
                <Download aria-hidden="true" className="mr-2 inline h-4 w-4" />
                {isExporting ? "Exportando" : "CSV"}
              </button>
            </div>
          </div>

          {chartData.length === 0 ? (
            <div className="mt-4">
              <EmptyState body="Crea un gasto o ingreso manual para ver la tendencia diaria real." title="Sin movimientos del mes" />
            </div>
          ) : (
            <div className="mt-4 h-64">
              <ResponsiveContainer height="100%" width="100%">
                <AreaChart data={chartData} margin={{ bottom: 0, left: 0, right: 0, top: 8 }}>
                  <XAxis axisLine={false} dataKey="label" tick={{ fill: "#A1A1AA", fontSize: 12 }} tickLine={false} />
                  <YAxis
                    axisLine={false}
                    tick={{ fill: "#71717A", fontSize: 12 }}
                    tickFormatter={formatCompactCurrency}
                    tickLine={false}
                    width={44}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#111113",
                      border: "1px solid #242428",
                      borderRadius: 8,
                      color: "#F4F4F5"
                    }}
                    formatter={(value, name) => [formatCurrency(Number(value)), name === "income" ? "Ingresos" : "Gastos"]}
                  />
                  <Area dataKey="expense" fill="#EF4444" fillOpacity={0.14} stroke="#EF4444" strokeWidth={2} type="monotone" />
                  <Area dataKey="income" fill="#22C55E" fillOpacity={0.12} stroke="#22C55E" strokeWidth={2} type="monotone" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <CategoryRanking
          emptyBody="Cuando registres ingresos por clases u otra fuente, apareceran aca."
          items={overview?.income_categories ?? []}
          title="Ingresos por categoria"
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <div className="panel p-4">
          <h2 className="text-base font-semibold">Mes actual vs anterior</h2>
          <p className="mt-1 text-sm text-muted">Comparado con {overview?.period_comparison?.previous_label ?? "el mes anterior"}.</p>
          <div className="mt-4 space-y-3">
            <DeltaLine
              label="Gasto"
              percent={overview?.period_comparison?.expense_delta_percent}
              value={overview?.period_comparison?.expense_delta ?? 0}
            />
            <DeltaLine
              label="Ingreso"
              percent={overview?.period_comparison?.income_delta_percent}
              positiveGood
              value={overview?.period_comparison?.income_delta ?? 0}
            />
            <DeltaLine label="Balance" positiveGood value={overview?.period_comparison?.net_balance_delta ?? 0} />
          </div>
        </div>
        <DailyHeatmap overview={overview} />
        <InsightList insights={overview?.insights ?? []} />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <BudgetPanel budgets={overview?.budget_progress ?? []} />
        <PersonIncomeList people={overview?.class_income_by_person ?? []} />
        <CategoryRanking
          emptyBody="Cuando una compra tenga desglose, sus partes apareceran como compra mixta."
          items={overview?.mixed_purchase_totals ?? []}
          title="Compras mixtas"
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <ObligationList emptyBody="No hay deuda por cobrar agrupada por persona." items={overview?.receivables_by_person ?? []} title="Por cobrar por persona" />
        <ObligationList emptyBody="No hay deuda por pagar agrupada por persona." items={overview?.payables_by_person ?? []} title="Por pagar por persona" />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <CategoryRanking
          emptyBody="Cuando registres gastos, el ranking usara desgloses si existen."
          items={overview?.expense_categories ?? []}
          title="Gasto por categoria"
        />

        <div className="panel p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">Ranking de comercios</h2>
              <p className="text-sm text-muted">Top del mes actual.</p>
            </div>
            <button
              className="focus-ring rounded-[8px] border border-border px-3 py-2 text-sm text-muted hover:text-text"
              onClick={() => setModalOpen(true)}
              type="button"
            >
              Preparar Gmail
            </button>
          </div>
          <div className="mt-4 space-y-3">
            {(overview?.merchants ?? []).length === 0 ? (
              <EmptyState body="Los comercios apareceran cuando existan gastos manuales o importados." title="Sin comercios" />
            ) : (
              overview?.merchants.map((merchant) => (
                <div className="flex items-center justify-between gap-3 border-b border-border/70 pb-3 text-sm" key={merchant.name}>
                  <div className="min-w-0">
                    <p className="truncate font-medium text-text">{merchant.name}</p>
                    <p className="text-xs text-subtle">{merchant.count} movimientos</p>
                  </div>
                  <span className="font-semibold text-text">{formatCurrency(toNumber(merchant.amount))}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
        <div className="panel min-w-0 p-4">
          <div className="mb-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-semibold">Ultimos movimientos reales</h2>
              <p className="text-sm text-muted">Al crear transacciones manuales, esta tabla se actualiza al volver al dashboard.</p>
            </div>
          </div>
          <DataTable columns={columns} getRowKey={(row) => row.id} rows={overview?.recent_transactions ?? []} />
        </div>

        <div className="min-w-0 space-y-4">
          <div className="panel p-4">
            <h2 className="text-base font-semibold">Cuentas por cobrar</h2>
            <p className="mt-1 text-sm text-muted">Saldo pendiente separado de ingresos y gastos.</p>
            <div className="mt-4 space-y-3">
              {(overview?.pending_receivables ?? []).length === 0 ? (
                <EmptyState body="Registra una deuda desde Transacciones para verla aca." title="Nada pendiente" />
              ) : (
                overview?.pending_receivables.map((receivable) => (
                  <div className="flex items-start justify-between gap-3 border-b border-border/70 pb-3 text-sm" key={receivable.id}>
                    <div className="min-w-0">
                      <p className="truncate font-medium text-text">{receivable.person_name}</p>
                      <p className="truncate text-xs text-subtle">{receivable.title}</p>
                    </div>
                    <span className="font-semibold text-warning">{formatCurrency(toNumber(receivable.remaining_amount), receivable.currency)}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="panel p-4">
            <h2 className="text-base font-semibold">Compras por desglosar</h2>
            <p className="mt-1 text-sm text-muted">Supermercados sin `transaction_splits`.</p>
            <div className="mt-4 space-y-3">
              {(overview?.unallocated_supermarkets ?? []).length === 0 ? (
                <EmptyState body="Las compras mixtas desglosadas desaparecen de esta lista." title="Sin pendientes" />
              ) : (
                overview?.unallocated_supermarkets.map((transaction) => (
                  <div className="flex items-start justify-between gap-3 border-b border-border/70 pb-3 text-sm" key={transaction.id}>
                    <div className="min-w-0">
                      <p className="truncate font-medium text-text">{transaction.merchant_name}</p>
                      <p className="text-xs text-subtle">{formatDateLabel(transaction.occurred_at)}</p>
                    </div>
                    <span className="font-semibold text-text">{formatCurrency(toNumber(transaction.amount), transaction.currency)}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <div className="panel p-4">
          <h2 className="text-base font-semibold">Movimientos por revisar</h2>
          <p className="mt-1 text-sm text-muted">Baja confianza o datos incompletos.</p>
          <div className="mt-4 space-y-3">
            {(overview?.review_transactions ?? []).length === 0 ? (
              <EmptyState body="No hay movimientos marcados para revision en este periodo." title="Todo clasificado" />
            ) : (
              overview?.review_transactions.map((transaction) => (
                <div className="flex items-start justify-between gap-3 border-b border-border/70 pb-3 text-sm" key={transaction.id}>
                  <div className="min-w-0">
                    <p className="truncate font-medium text-text">{transaction.merchant_name ?? transaction.counterparty ?? "Movimiento"}</p>
                    <p className="text-xs text-subtle">{transaction.category_name ?? "Sin categoria"}</p>
                  </div>
                  <span className="font-semibold text-warning">{formatCurrency(toNumber(transaction.amount), transaction.currency)}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="panel p-4">
          <h2 className="text-base font-semibold">Posibles suscripciones</h2>
          <p className="mt-1 text-sm text-muted">Mismo comercio, monto similar e intervalo mensual.</p>
          <div className="mt-4 space-y-3">
            {(overview?.subscriptions ?? []).length === 0 ? (
              <EmptyState body="Cuando haya pagos repetidos mensuales, FinEx los mostrara aca." title="Sin patrones mensuales" />
            ) : (
              overview?.subscriptions.map((subscription) => (
                <div className="flex items-start justify-between gap-3 border-b border-border/70 pb-3 text-sm" key={subscription.merchant_name}>
                  <div className="min-w-0">
                    <p className="truncate font-medium text-text">{subscription.merchant_name}</p>
                    <p className="text-xs text-subtle">{subscription.count} cargos detectados</p>
                  </div>
                  <span className="font-semibold text-text">{formatCurrency(toNumber(subscription.average_amount))}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <div className="panel p-4">
          <h2 className="text-base font-semibold">Tarjetas y cuentas</h2>
          <p className="mt-1 text-sm text-muted">Saldo estimado con snapshots locales y movimientos asignados.</p>
          <div className="mt-4 space-y-3">
            {(overview?.financial_accounts ?? []).length === 0 ? (
              <EmptyState body="Crea tarjetas o cuentas en Ajustes para estimar saldos." title="Sin cuentas" />
            ) : (
              overview?.financial_accounts.map((account) => {
                const tone = accountTone(account.card_art_variant, account.account_type);
                const isCredit = account.account_type === "credit_card";
                return (
                  <ColorCard hover className="p-4" key={account.account_id} tone={tone}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-text">{account.name}</p>
                        <p className="truncate text-xs text-subtle">
                          {account.institution ?? "Sin institucion"} · {formatFinancialAccountType(account.account_type)} · {account.currency}
                        </p>
                      </div>
                      <span className="shrink-0 rounded-[8px] border border-border/60 bg-bg/30 px-2 py-1 text-[11px] tabular-nums text-muted">
                        {account.last_four ? `•••• ${account.last_four}` : "Sin dígitos"}
                      </span>
                    </div>
                    {isCredit ? (
                      <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <p className="text-subtle">Usado</p>
                          <p className="text-base font-semibold tabular-nums text-text">
                            {formatCurrency(Math.abs(toNumber(account.used_credit_amount ?? account.balance)), account.currency)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-subtle">Disponible</p>
                          <p className="text-base font-semibold tabular-nums text-text">
                            {account.available_credit_amount ? formatCurrency(toNumber(account.available_credit_amount), account.currency) : "Sin cupo"}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="mt-4 flex items-end justify-between gap-3">
                        <div>
                          <p className="text-xs text-subtle">Saldo estimado</p>
                          <p className="text-xl font-semibold tabular-nums text-text">{formatCurrency(toNumber(account.balance), account.currency)}</p>
                        </div>
                        <span className="text-[11px] text-subtle">{account.transaction_count} movimientos</span>
                      </div>
                    )}
                    <p className="mt-3 border-t border-border/50 pt-2 text-[11px] text-subtle">
                      {isCredit
                        ? `Estado ${account.statement_amount ? formatCurrency(toNumber(account.statement_amount), account.statement_currency ?? account.currency) : "sin estado"} · `
                        : ""}
                      Delta mes {formatCurrency(toNumber(account.month_delta), account.currency)}
                    </p>
                  </ColorCard>
                );
              })
            )}
          </div>
        </div>

        <div className="panel p-4">
          <h2 className="text-base font-semibold">Inversiones</h2>
          <p className="mt-1 text-sm text-muted">Aportes y rescates separados de gasto/ingreso.</p>
          <div className="mt-4 space-y-3">
            {(overview?.investment_accounts ?? []).length === 0 ? (
              <EmptyState body="Crea una cuenta de inversion en Ajustes." title="Sin inversiones" />
            ) : (
              overview?.investment_accounts.map((account) => (
                <ColorCard hover className="p-4" key={account.account_id} tone="info">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-text">{account.name}</p>
                      <p className="truncate text-xs text-subtle">{account.institution ?? "Sin institucion"} · {formatInvestmentAccountType(account.account_type)}</p>
                    </div>
                    <span className="shrink-0 text-lg font-semibold tabular-nums text-info">{formatCurrency(toNumber(account.current_value), account.currency)}</span>
                  </div>
                  <p className="mt-3 border-t border-border/50 pt-2 text-[11px] text-subtle">
                    Aportes {formatCurrency(toNumber(account.month_invested), account.currency)} · Retiros{" "}
                    {formatCurrency(toNumber(account.month_withdrawn), account.currency)}
                  </p>
                </ColorCard>
              ))
            )}
          </div>
        </div>

        <div className="panel p-4">
          <h2 className="text-base font-semibold">Sin cuenta asignada</h2>
          <p className="mt-1 text-sm text-muted">Movimientos que necesitan cuenta/tarjeta para saldos.</p>
          <div className="mt-4 space-y-3">
            {(overview?.unassigned_account_transactions ?? []).length === 0 ? (
              <EmptyState body="Los movimientos con cuenta asignada desaparecen de esta lista." title="Todo asignado" />
            ) : (
              overview?.unassigned_account_transactions.map((transaction) => (
                <div className="flex items-start justify-between gap-3 border-b border-border/70 pb-3 text-sm" key={transaction.id}>
                  <div className="min-w-0">
                    <p className="truncate font-medium text-text">{transaction.merchant_name ?? transaction.counterparty ?? "Movimiento"}</p>
                    <p className="text-xs text-subtle">{formatDateLabel(transaction.occurred_at)}</p>
                  </div>
                  <span className="font-semibold text-warning">{formatCurrency(toNumber(transaction.amount), transaction.currency)}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <Modal onClose={() => setModalOpen(false)} open={modalOpen} title="Conexion Gmail">
        <p className="text-sm text-muted">
          FinEx usara Gmail API con OAuth y permisos minimos cuando actives una conexion real. Por ahora esta vista queda preparada para el flujo seguro.
        </p>
      </Modal>
    </div>
  );
}
