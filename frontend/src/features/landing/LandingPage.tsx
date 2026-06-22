import {
  ArrowRight,
  BarChart3,
  Check,
  CreditCard,
  Github,
  HandCoins,
  Inbox,
  Lock,
  Mail,
  ScanLine,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Wallet,
  Zap
} from "lucide-react";
import { useState, type ReactNode } from "react";

import { useCountUp, useReveal } from "./hooks";

type LandingPageProps = {
  onEnter: () => void;
  onExploreDemo: () => void;
};

const githubUrl = import.meta.env.VITE_FINEX_GITHUB_URL || "https://github.com/";

/* ---------------- Reveal wrapper ---------------- */

function Reveal({ children, className = "", delay = 0 }: { children: ReactNode; className?: string; delay?: number }) {
  const { ref, visible } = useReveal();
  return (
    <div
      ref={ref}
      className={`fx-reveal ${visible ? "is-visible" : ""} ${className}`}
      style={{ transitionDelay: visible ? `${delay}ms` : "0ms" }}
    >
      {children}
    </div>
  );
}

/* ---------------- Brand mark ---------------- */

function BrandMark({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <div className="flex h-9 w-9 items-center justify-center rounded-[10px] border border-accent/40 bg-accent/10 text-sm font-semibold text-accent shadow-[0_0_24px_rgba(34,197,94,0.25)]">
        FX
      </div>
      <span className="text-base font-semibold tracking-tight">FinEx</span>
    </div>
  );
}

/* ---------------- Mock previews for the product tour ---------------- */

function MiniBars() {
  const heights = [38, 52, 30, 66, 44, 78, 58, 90, 72, 96, 62, 84];
  return (
    <div className="flex h-24 items-end gap-1.5">
      {heights.map((h, i) => (
        <div key={i} className="relative flex-1 overflow-hidden rounded-t-[3px] bg-surface2">
          <div
            className="absolute bottom-0 left-0 w-full rounded-t-[3px] bg-gradient-to-t from-accent/70 to-info/70"
            style={{ height: `${h}%`, animation: `fx-grow 0.9s cubic-bezier(0.16,1,0.3,1) ${i * 0.05}s both` }}
          />
        </div>
      ))}
    </div>
  );
}

function MockDashboard() {
  const tiles = [
    { label: "Liquidez", value: "$2.840.500", tone: "text-text" },
    { label: "Gasto del mes", value: "$1.284.300", tone: "text-warning" },
    { label: "Balance real", value: "+$612.200", tone: "text-accent" }
  ];
  const cats = [
    { name: "Supermercado", pct: 92, color: "#22C55E" },
    { name: "Suscripciones", pct: 58, color: "#38BDF8" },
    { name: "Transporte", pct: 40, color: "#F59E0B" }
  ];
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2.5">
        {tiles.map((t) => (
          <div key={t.label} className="panel-tight p-3">
            <p className="text-[11px] text-muted">{t.label}</p>
            <p className={`mt-1 text-sm font-semibold tabular-nums ${t.tone}`}>{t.value}</p>
          </div>
        ))}
      </div>
      <div className="panel-tight p-3">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-[11px] text-muted">Tendencia mensual</p>
          <span className="flex items-center gap-1 text-[11px] text-accent">
            <TrendingUp className="h-3 w-3" /> +8,4%
          </span>
        </div>
        <MiniBars />
      </div>
      <div className="panel-tight space-y-2.5 p-3">
        {cats.map((c) => (
          <div key={c.name} className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-muted">{c.name}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-surface">
              <div className="h-full rounded-full" style={{ width: `${c.pct}%`, backgroundColor: c.color }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MockMovements() {
  const rows = [
    { merchant: "Lider Express", cat: "Supermercado", color: "#22C55E", amount: "-$48.990" },
    { merchant: "Spotify", cat: "Suscripciones", color: "#38BDF8", amount: "-$5.300" },
    { merchant: "Clase de inglés", cat: "Ingreso", color: "#A78BFA", amount: "+$25.000" },
    { merchant: "Uber", cat: "Transporte", color: "#F59E0B", amount: "-$6.740" },
    { merchant: "Farmacia", cat: "Salud", color: "#EF4444", amount: "-$12.450" }
  ];
  return (
    <div className="panel-tight divide-y divide-border">
      {rows.map((r) => (
        <div key={r.merchant} className="flex items-center justify-between gap-3 px-3 py-2.5">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: r.color }} />
            <div className="min-w-0">
              <p className="truncate text-xs font-medium">{r.merchant}</p>
              <p className="text-[11px] text-subtle">{r.cat}</p>
            </div>
          </div>
          <span className={`shrink-0 text-xs font-semibold tabular-nums ${r.amount.startsWith("+") ? "text-accent" : "text-text"}`}>
            {r.amount}
          </span>
        </div>
      ))}
    </div>
  );
}

function MockObligations() {
  const people = [
    { name: "Camila", note: "A favor mío", amount: "+$35.000", tone: "text-accent" },
    { name: "Diego", note: "En contra mía", amount: "-$18.500", tone: "text-danger" },
    { name: "Equipo viaje", note: "Cuadrado", amount: "$0", tone: "text-muted" }
  ];
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2.5">
        <div className="panel-tight p-3">
          <p className="text-[11px] text-muted">Por cobrar</p>
          <p className="mt-1 text-sm font-semibold text-accent tabular-nums">$72.000</p>
        </div>
        <div className="panel-tight p-3">
          <p className="text-[11px] text-muted">Por pagar</p>
          <p className="mt-1 text-sm font-semibold text-danger tabular-nums">$18.500</p>
        </div>
      </div>
      <div className="panel-tight divide-y divide-border">
        {people.map((p) => (
          <div key={p.name} className="flex items-center justify-between px-3 py-2.5">
            <div>
              <p className="text-xs font-medium">{p.name}</p>
              <p className="text-[11px] text-subtle">{p.note}</p>
            </div>
            <span className={`text-xs font-semibold tabular-nums ${p.tone}`}>{p.amount}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MockImport() {
  return (
    <div className="space-y-3">
      <div className="panel-tight p-3">
        <div className="flex items-center gap-2 text-[11px] text-muted">
          <Mail className="h-3.5 w-3.5 text-info" />
          <span className="truncate">Banco · Compra aprobada</span>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-subtle">
          "Compra por <span className="text-text">$48.990</span> en <span className="text-text">LIDER EXPRESS</span> con tarjeta terminada en 4471."
        </p>
      </div>
      <div className="panel-tight space-y-2 p-3">
        <p className="text-[11px] uppercase tracking-wide text-subtle">Detectado por FinEx</p>
        {[
          { k: "Monto", v: "$48.990" },
          { k: "Comercio", v: "Lider Express" },
          { k: "Categoría sugerida", v: "Supermercado" },
          { k: "Cuenta", v: "Crédito ··4471" }
        ].map((f) => (
          <div key={f.k} className="flex items-center justify-between text-xs">
            <span className="text-muted">{f.k}</span>
            <span className="font-medium">{f.v}</span>
          </div>
        ))}
        <button
          type="button"
          className="mt-1 flex w-full items-center justify-center gap-1.5 rounded-[8px] bg-accent/15 px-3 py-1.5 text-xs font-medium text-accent transition hover:bg-accent/25"
        >
          <Check className="h-3.5 w-3.5" /> Confirmar movimiento
        </button>
      </div>
    </div>
  );
}

function MockAccounts() {
  const cards = [
    { name: "Cuenta corriente", cur: "CLP", value: "$2.140.500", grad: "from-accent/25 to-accent/5" },
    { name: "Tarjeta crédito", cur: "CLP", value: "$320.000", grad: "from-info/25 to-info/5" },
    { name: "Inversión USD", cur: "USD", value: "$1.280", grad: "from-warning/25 to-warning/5" }
  ];
  return (
    <div className="space-y-2.5">
      {cards.map((c) => (
        <div key={c.name} className={`relative overflow-hidden rounded-[10px] border border-border bg-gradient-to-br ${c.grad} p-3`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium">{c.name}</p>
              <p className="text-[11px] text-subtle">{c.cur}</p>
            </div>
            <span className="text-sm font-semibold tabular-nums">{c.value}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function MockRules() {
  const rules = [
    { from: "Spotify", to: "Suscripciones", conf: 99 },
    { from: "Uber / Rappi", to: "Transporte", conf: 96 },
    { from: "Lider", to: "Supermercado", conf: 94 }
  ];
  return (
    <div className="panel-tight divide-y divide-border">
      {rules.map((r) => (
        <div key={r.from} className="flex items-center justify-between gap-3 px-3 py-3">
          <div className="flex items-center gap-2 text-xs">
            <span className="rounded-[6px] bg-surface px-2 py-0.5 font-medium">{r.from}</span>
            <ArrowRight className="h-3 w-3 text-subtle" />
            <span className="rounded-[6px] bg-accent/10 px-2 py-0.5 font-medium text-accent">{r.to}</span>
          </div>
          <span className="text-[11px] text-muted tabular-nums">{r.conf}%</span>
        </div>
      ))}
    </div>
  );
}

/* ---------------- Product tour data ---------------- */

const tourFeatures = [
  {
    id: "dashboard",
    icon: BarChart3,
    title: "Dashboard inteligente",
    desc: "Liquidez, gasto e ingreso del mes, balance real, heatmap diario, proyección de cierre e insights de anomalías en una sola vista.",
    render: () => <MockDashboard />
  },
  {
    id: "movements",
    icon: CreditCard,
    title: "Movimientos en segundos",
    desc: "Registra gastos e ingresos con un flujo enfocado, desglosa compras mixtas y edita todo desde un panel lateral sin perder el contexto.",
    render: () => <MockMovements />
  },
  {
    id: "obligations",
    icon: HandCoins,
    title: "Cobrar y pagar, ordenado",
    desc: "Cuentas por cobrar y por pagar con balance por persona: sabes al instante qué queda a favor tuyo y qué debes, sin mezclarlo con tu gasto.",
    render: () => <MockObligations />
  },
  {
    id: "import",
    icon: Inbox,
    title: "Importa desde Gmail",
    desc: "Conecta Gmail por OAuth y FinEx lee tus correos bancarios: detecta monto, comercio, tarjeta y categoría. Tú solo revisas y confirmas.",
    render: () => <MockImport />
  },
  {
    id: "accounts",
    icon: Wallet,
    title: "Cuentas e inversiones",
    desc: "Tarjetas, cuentas y saldos multi-moneda. Las inversiones viven separadas del gasto mensual para que tu patrimonio sea claro.",
    render: () => <MockAccounts />
  },
  {
    id: "rules",
    icon: Zap,
    title: "Clasificación por reglas",
    desc: "Un motor determinístico aprende de tus correcciones y categoriza solo. Cada cambio puede convertirse en una regla reutilizable.",
    render: () => <MockRules />
  }
] as const;

/* ---------------- Stats ---------------- */

function Stat({ target, suffix = "", label, decimals = 0 }: { target: number; suffix?: string; label: string; decimals?: number }) {
  const { ref, visible } = useReveal();
  const value = useCountUp(target, visible);
  const display = decimals > 0 ? value.toFixed(decimals) : Math.round(value).toLocaleString("es-CL");
  return (
    <div ref={ref} className="text-center">
      <p className="text-3xl font-semibold tracking-tight text-text sm:text-4xl">
        <span className="fx-gradient-text">{display}</span>
        {suffix}
      </p>
      <p className="mt-1 text-xs text-muted sm:text-sm">{label}</p>
    </div>
  );
}

/* ---------------- Page ---------------- */

export function LandingPage({ onEnter, onExploreDemo }: LandingPageProps) {
  const [activeTour, setActiveTour] = useState<string>(tourFeatures[0].id);
  const active = tourFeatures.find((f) => f.id === activeTour) ?? tourFeatures[0];

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-bg text-text">
      {/* Ambient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="fx-orb h-[460px] w-[460px] -left-32 -top-24 bg-accent/20" style={{ animationDelay: "0s" }} />
        <div className="fx-orb h-[420px] w-[420px] right-[-10%] top-[8%] bg-info/15" style={{ animationDelay: "-6s" }} />
        <div className="fx-orb h-[380px] w-[380px] left-[30%] top-[55%] bg-[#A78BFA]/10" style={{ animationDelay: "-11s" }} />
      </div>
      <div className="fx-grid pointer-events-none fixed inset-0 h-[70vh]" />

      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-border/60 bg-bg/70 backdrop-blur-xl">
        <div className="mx-auto flex h-16 w-full max-w-[1180px] items-center justify-between px-5">
          <BrandMark />
          <nav className="hidden items-center gap-7 text-sm text-muted md:flex">
            <a className="transition hover:text-text" href="#tour">Funcionalidades</a>
            <a className="transition hover:text-text" href="#flow">Cómo funciona</a>
            <a className="transition hover:text-text" href="#privacy">Privacidad</a>
          </nav>
          <button
            type="button"
            onClick={onEnter}
            className="focus-ring flex items-center gap-1.5 rounded-[8px] border border-border bg-surface2 px-3.5 py-1.5 text-sm font-medium transition hover:border-accent/40 hover:text-accent"
          >
            Entrar <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </header>

      <main className="relative z-10">
        {/* Hero */}
        <section className="mx-auto w-full max-w-[1180px] px-5 pb-16 pt-16 sm:pt-24">
          <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
            <div>
              <Reveal>
                <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface2/70 px-3 py-1 text-xs text-muted">
                  <span className="relative flex h-2 w-2">
                    <span className="fx-pulse-ring absolute inline-flex h-2 w-2 rounded-full bg-accent" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
                  </span>
                  Local-first · privado por diseño
                </span>
              </Reveal>
              <Reveal delay={80}>
                <h1 className="mt-5 text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
                  Tus finanzas, <span className="fx-gradient-text">claras</span> antes de que llegue la factura.
                </h1>
              </Reveal>
              <Reveal delay={160}>
                <p className="mt-5 max-w-xl text-base leading-relaxed text-muted sm:text-lg">
                  FinEx registra, importa desde Gmail, clasifica y visualiza tus gastos personales.
                  Todo en tu equipo, sin nube, con un dashboard que entiendes de un vistazo.
                </p>
              </Reveal>
              <Reveal delay={240}>
                <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                  <button
                    type="button"
                    onClick={onExploreDemo}
                    className="focus-ring group flex items-center justify-center gap-2 rounded-[10px] bg-accent px-5 py-3 text-sm font-semibold text-bg shadow-[0_8px_30px_rgba(34,197,94,0.35)] transition hover:shadow-[0_8px_40px_rgba(34,197,94,0.5)]"
                  >
                    <Sparkles className="h-4 w-4" />
                    Ver demo
                    <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                  </button>
                  <a
                    href={githubUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="focus-ring flex items-center justify-center gap-2 rounded-[10px] border border-border bg-surface2/60 px-5 py-3 text-sm font-medium transition hover:border-accent/40 hover:text-accent"
                  >
                    <Github className="h-4 w-4" />
                    Ver en GitHub
                  </a>
                </div>
              </Reveal>
              <Reveal delay={320}>
                <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-subtle">
                  <span className="flex items-center gap-1.5"><Lock className="h-3.5 w-3.5 text-accent" /> Datos en SQLite local</span>
                  <span className="flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-accent" /> Sin secretos en la nube</span>
                  <span className="flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-accent" /> Multi-moneda</span>
                </div>
              </Reveal>
            </div>

            {/* Floating dashboard preview */}
            <Reveal delay={200}>
              <div className="relative">
                <div className="fx-float-slow panel relative z-10 p-4 shadow-[0_30px_80px_rgba(0,0,0,0.5)]">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full bg-danger/70" />
                      <span className="h-2.5 w-2.5 rounded-full bg-warning/70" />
                      <span className="h-2.5 w-2.5 rounded-full bg-accent/70" />
                    </div>
                    <span className="text-[11px] text-subtle">Dashboard · Junio</span>
                  </div>
                  <MockDashboard />
                </div>
                <div className="fx-float absolute -bottom-6 -left-6 z-20 hidden rounded-[12px] border border-border bg-surface/90 p-3 backdrop-blur sm:block" style={{ animationDelay: "-2s" }}>
                  <div className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-[8px] bg-accent/15 text-accent">
                      <TrendingUp className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-[11px] text-muted">Balance real</p>
                      <p className="text-sm font-semibold text-accent">+$612.200</p>
                    </div>
                  </div>
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        {/* Stats */}
        <section className="border-y border-border/60 bg-surface/30">
          <div className="mx-auto grid w-full max-w-[1180px] grid-cols-2 gap-8 px-5 py-10 sm:grid-cols-4">
            <Stat target={7} label="Módulos integrados" />
            <Stat target={13} suffix="+" label="Categorías base" />
            <Stat target={100} suffix="%" label="Local y privado" />
            <Stat target={0} label="Datos en la nube" />
          </div>
        </section>

        {/* Interactive product tour */}
        <section id="tour" className="mx-auto w-full max-w-[1180px] px-5 py-20">
          <Reveal className="mx-auto max-w-2xl text-center">
            <p className="text-sm font-medium text-accent">El producto</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Todo lo que necesitas, en un solo lugar</h2>
            <p className="mt-3 text-muted">Explora cada módulo. Haz clic para ver una vista previa real de la app.</p>
          </Reveal>

          <div className="mt-12 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            {/* Tabs */}
            <div className="flex flex-col gap-2.5">
              {tourFeatures.map((f) => {
                const Icon = f.icon;
                const isActive = f.id === activeTour;
                return (
                  <button
                    key={f.id}
                    type="button"
                    onMouseEnter={() => setActiveTour(f.id)}
                    onClick={() => setActiveTour(f.id)}
                    className={`focus-ring group flex items-start gap-3.5 rounded-[12px] border p-4 text-left transition ${
                      isActive
                        ? "border-accent/40 bg-surface2 shadow-[0_0_30px_rgba(34,197,94,0.08)]"
                        : "border-border bg-surface/40 hover:border-border hover:bg-surface2/60"
                    }`}
                  >
                    <div
                      className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] border transition ${
                        isActive ? "border-accent/40 bg-accent/15 text-accent" : "border-border bg-surface2 text-muted group-hover:text-text"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <p className={`text-sm font-semibold transition ${isActive ? "text-text" : "text-muted group-hover:text-text"}`}>{f.title}</p>
                      <p
                        className={`mt-1 overflow-hidden text-xs leading-relaxed text-subtle transition-all duration-300 ${
                          isActive ? "max-h-24 opacity-100" : "max-h-0 opacity-0 sm:max-h-24 sm:opacity-100"
                        }`}
                      >
                        {f.desc}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Preview */}
            <div className="panel relative overflow-hidden p-5 lg:p-6">
              <div className="pointer-events-none absolute -right-20 -top-20 h-48 w-48 rounded-full bg-accent/10 blur-3xl" />
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <active.icon className="h-4 w-4 text-accent" />
                  <span className="text-sm font-medium">{active.title}</span>
                </div>
                <span className="text-[11px] text-subtle">Vista previa</span>
              </div>
              <div key={active.id} className="fx-reveal is-visible">
                {active.render()}
              </div>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="flow" className="border-y border-border/60 bg-surface/30">
          <div className="mx-auto w-full max-w-[1180px] px-5 py-20">
            <Reveal className="mx-auto max-w-2xl text-center">
              <p className="text-sm font-medium text-accent">Cómo funciona</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">De tus correos a un dashboard claro</h2>
            </Reveal>
            <div className="mt-12 grid gap-5 md:grid-cols-3">
              {[
                { n: "01", icon: ScanLine, title: "Importa o registra", desc: "Conecta Gmail o anota un movimiento a mano. FinEx lee monto, comercio y cuenta automáticamente." },
                { n: "02", icon: Zap, title: "Clasifica solo", desc: "Las reglas categorizan cada movimiento. Tú corriges una vez y FinEx aprende para la próxima." },
                { n: "03", icon: BarChart3, title: "Visualiza y decide", desc: "Dashboard con balance real, tendencias e insights para llegar tranquilo a fin de mes." }
              ].map((step, i) => {
                const Icon = step.icon;
                return (
                  <Reveal key={step.n} delay={i * 120}>
                    <div className="panel h-full p-6">
                      <div className="flex items-center justify-between">
                        <div className="flex h-10 w-10 items-center justify-center rounded-[10px] border border-accent/30 bg-accent/10 text-accent">
                          <Icon className="h-5 w-5" />
                        </div>
                        <span className="text-2xl font-semibold text-border">{step.n}</span>
                      </div>
                      <h3 className="mt-5 text-lg font-semibold">{step.title}</h3>
                      <p className="mt-2 text-sm leading-relaxed text-muted">{step.desc}</p>
                    </div>
                  </Reveal>
                );
              })}
            </div>
          </div>
        </section>

        {/* Privacy */}
        <section id="privacy" className="mx-auto w-full max-w-[1180px] px-5 py-20">
          <div className="panel relative overflow-hidden p-8 sm:p-12">
            <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-accent/10 blur-3xl" />
            <div className="relative grid items-center gap-10 lg:grid-cols-[1fr_0.8fr]">
              <div>
                <Reveal>
                  <span className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs text-accent">
                    <ShieldCheck className="h-3.5 w-3.5" /> Privacidad por defecto
                  </span>
                  <h2 className="mt-5 text-3xl font-semibold tracking-tight sm:text-4xl">Tus datos nunca salen de tu equipo</h2>
                  <p className="mt-4 max-w-lg text-muted">
                    FinEx es local-first: la información vive en una base SQLite en tu máquina.
                    Las credenciales de Gmail se guardan localmente, fuera del repositorio, y nada se sincroniza a servidores externos.
                  </p>
                </Reveal>
              </div>
              <Reveal delay={120}>
                <div className="space-y-3">
                  {[
                    { icon: Lock, t: "Base de datos local", d: "SQLite en tu disco, sin nube." },
                    { icon: ShieldCheck, t: "OAuth seguro", d: "Tokens de Gmail guardados localmente." },
                    { icon: Check, t: "Tú tienes el control", d: "Exporta a CSV cuando quieras." }
                  ].map((item) => {
                    const Icon = item.icon;
                    return (
                      <div key={item.t} className="panel-tight flex items-center gap-3 p-3.5">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] bg-accent/10 text-accent">
                          <Icon className="h-4 w-4" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">{item.t}</p>
                          <p className="text-xs text-muted">{item.d}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Reveal>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="mx-auto w-full max-w-[1180px] px-5 pb-24">
          <Reveal>
            <div className="relative overflow-hidden rounded-[18px] border border-accent/30 bg-gradient-to-br from-accent/15 via-surface to-info/10 p-10 text-center sm:p-16">
              <div className="pointer-events-none absolute inset-0 fx-grid opacity-40" />
              <div className="relative">
                <h2 className="mx-auto max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
                  Llega a fin de mes sin sorpresas
                </h2>
                <p className="mx-auto mt-4 max-w-xl text-muted">
                  Empieza a entender tu dinero hoy. Sin registro, sin nube, sin fricción.
                </p>
                <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                  <button
                    type="button"
                    onClick={onExploreDemo}
                    className="focus-ring group flex items-center justify-center gap-2 rounded-[10px] bg-accent px-6 py-3 text-sm font-semibold text-bg shadow-[0_8px_30px_rgba(34,197,94,0.35)] transition hover:shadow-[0_8px_40px_rgba(34,197,94,0.55)]"
                  >
                    <Sparkles className="h-4 w-4" /> Ver demo
                    <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                  </button>
                  <button
                    type="button"
                    onClick={onEnter}
                    className="focus-ring flex items-center justify-center gap-2 rounded-[10px] border border-border bg-surface2/60 px-6 py-3 text-sm font-medium transition hover:border-accent/40 hover:text-accent"
                  >
                    Entrar a la app
                  </button>
                </div>
              </div>
            </div>
          </Reveal>
        </section>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-border/60">
        <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-4 px-5 py-8 lg:flex-row lg:items-center lg:justify-between">
          <BrandMark />
          <div className="flex flex-col items-start gap-3 text-xs text-subtle sm:flex-row sm:flex-wrap sm:items-center sm:justify-end">
            <span>Dashboard personal de finanzas · local-first</span>
            <div className="flex flex-wrap items-center gap-2">
              <a
                href={githubUrl}
                target="_blank"
                rel="noreferrer"
                className="rounded-full border border-border bg-surface2/60 px-3 py-1.5 text-muted transition hover:border-accent/40 hover:text-text"
              >
                GitHub
              </a>
              <a
                href="https://choosealicense.com/licenses/mit/"
                target="_blank"
                rel="noreferrer"
                className="rounded-full border border-border bg-surface2/60 px-3 py-1.5 text-muted transition hover:border-accent/40 hover:text-text"
              >
                Licencia MIT
              </a>
              <a
                href="#tour"
                className="rounded-full border border-border bg-surface2/60 px-3 py-1.5 text-muted transition hover:border-accent/40 hover:text-text"
              >
                Stack y producto
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
