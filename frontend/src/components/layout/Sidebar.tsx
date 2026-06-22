import { BarChart3, CreditCard, FlaskConical, HandCoins, Inbox, MailCheck, Settings, User, Wallet } from "lucide-react";
import { useState } from "react";

import { api } from "../../lib/api";
import { useSession } from "../../lib/sessionContext";

const navItems = [
  { label: "Dashboard", icon: BarChart3, view: "dashboard" },
  { label: "Movimientos", icon: CreditCard, view: "movements" },
  { label: "Obligaciones", icon: HandCoins, view: "obligations" },
  { label: "Importar", icon: Inbox, view: "import" },
  { label: "Correos", icon: MailCheck, view: "mailbox" },
  { label: "Cuentas", icon: Wallet, view: "accounts" },
  { label: "Configuracion", icon: Settings, view: "settings" }
];

type SidebarProps = {
  activeView: string;
  onNavigate: (view: string) => void;
  onExitToLanding?: () => void;
};

export function Sidebar({ activeView, onExitToLanding, onNavigate }: SidebarProps) {
  const { session, setSession, isDemo } = useSession();
  const [resetting, setResetting] = useState(false);
  const [resetMsg, setResetMsg] = useState<string | null>(null);

  async function handleResetDemo() {
    if (resetting) return;
    setResetting(true);
    setResetMsg(null);
    try {
      await api.resetDemoSession();
      setResetMsg("Demo reiniciada");
      // Reload page so all queries re-fetch from fresh demo DB
      setTimeout(() => window.location.reload(), 800);
    } catch {
      setResetMsg("Error al reiniciar");
    } finally {
      setResetting(false);
    }
  }

  return (
    <aside className="border-b border-border bg-surface/70 px-4 py-3 backdrop-blur-xl md:min-h-screen md:w-60 md:border-b-0 md:border-r md:px-3 md:py-4">
      {/* Logo + session badge */}
      <div className="flex items-center justify-between gap-3 md:block">
        <button
          className="focus-ring flex items-center gap-3 rounded-[10px] text-left transition hover:opacity-80 md:px-2"
          onClick={() => onExitToLanding?.()}
          type="button"
          title="Volver a la portada"
        >
          <div className={`flex h-9 w-9 items-center justify-center rounded-[10px] border text-sm font-semibold ${isDemo ? "border-warning/40 bg-warning/10 text-warning shadow-[0_0_24px_rgba(245,158,11,0.25)]" : "border-accent/40 bg-accent/10 text-accent shadow-[0_0_24px_rgba(34,197,94,0.25)]"}`}>
            FX
          </div>
          <div>
            <p className="text-sm font-semibold leading-tight">FinEx</p>
            <p className="text-xs text-subtle">{isDemo ? "Demo · Presentación" : "Control mensual"}</p>
          </div>
        </button>

        {/* Session switcher — visible inline on mobile, stacked on desktop */}
        <div className="md:mt-4 md:px-2">
          <div className="flex overflow-hidden rounded-[8px] border border-border text-xs">
            <button
              className={`flex flex-1 items-center justify-center gap-1 px-2 py-1.5 transition ${session === "personal" ? "bg-surface2 text-text" : "text-muted hover:bg-surface2/50 hover:text-text"}`}
              onClick={() => setSession("personal")}
              type="button"
              title="Sesión personal con tus datos reales"
            >
              <User className="h-3 w-3 shrink-0" aria-hidden="true" />
              <span className="hidden sm:inline md:inline">Personal</span>
            </button>
            <button
              className={`flex flex-1 items-center justify-center gap-1 px-2 py-1.5 transition ${session === "demo" ? "bg-warning/15 text-warning" : "text-muted hover:bg-surface2/50 hover:text-text"}`}
              onClick={() => setSession("demo")}
              type="button"
              title="Sesión demo con datos de presentación"
            >
              <FlaskConical className="h-3 w-3 shrink-0" aria-hidden="true" />
              <span className="hidden sm:inline md:inline">Demo</span>
            </button>
          </div>
        </div>
      </div>

      {/* Demo banner */}
      {isDemo && (
        <div className="mt-3 rounded-[8px] border border-warning/30 bg-warning/10 px-3 py-2 md:mx-0">
          <p className="text-xs font-medium text-warning">Modo presentación</p>
          <p className="mt-0.5 text-[11px] text-warning/70">Datos ficticios. Tu sesión personal no se ve afectada.</p>
          <button
            className="mt-2 w-full rounded-[6px] border border-warning/30 bg-warning/10 px-2 py-1 text-[11px] text-warning/80 transition hover:bg-warning/20 hover:text-warning disabled:opacity-50"
            disabled={resetting}
            onClick={handleResetDemo}
            type="button"
          >
            {resetting ? "Reiniciando…" : "Reiniciar datos demo"}
          </button>
          {resetMsg && <p className="mt-1 text-center text-[11px] text-warning/60">{resetMsg}</p>}
        </div>
      )}

      <nav className="mt-4 flex gap-2 overflow-x-auto md:block md:space-y-1 md:overflow-visible">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.view === activeView;
          return (
            <button
              className={`focus-ring flex shrink-0 items-center gap-2 rounded-[8px] px-3 py-2 text-sm transition md:w-full ${
                isActive
                  ? "border border-accent/30 bg-accent/10 text-text shadow-[0_0_20px_rgba(34,197,94,0.08)]"
                  : "border border-transparent text-muted hover:bg-surface2 hover:text-text"
              }`}
              key={item.label}
              onClick={() => onNavigate(item.view)}
              type="button"
            >
              <Icon aria-hidden="true" className={`h-4 w-4 ${isActive ? "text-accent" : ""}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
