import type { PropsWithChildren } from "react";

import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

type AppShellProps = PropsWithChildren<{
  activeView: string;
  onNavigate: (view: string) => void;
  onExitToLanding?: () => void;
  title: string;
  subtitle?: string;
}>;

export function AppShell({ activeView, children, onExitToLanding, onNavigate, subtitle, title }: AppShellProps) {
  const searchLabels: Record<string, string> = {
    dashboard: "Buscar en dashboard",
    movements: "Buscar movimientos",
    obligations: "Buscar obligaciones",
    import: "Buscar correos a importar",
    mailbox: "Buscar correos",
    accounts: "Buscar cuentas",
    settings: "Buscar ajustes"
  };
  const searchPlaceholders: Record<string, string> = {
    dashboard: "Buscar en dashboard...",
    movements: "Buscar movimiento...",
    obligations: "Buscar obligacion...",
    import: "Buscar correo...",
    mailbox: "Buscar correo...",
    accounts: "Buscar cuenta...",
    settings: "Buscar ajuste..."
  };

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-bg text-text">
      {/* Ambient background — echoes the landing, kept very subtle behind the app */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
        <div className="fx-orb h-[380px] w-[380px] -left-32 -top-32 bg-accent/10" style={{ animationDelay: "0s" }} />
        <div className="fx-orb h-[340px] w-[340px] right-[-12%] top-[12%] bg-info/[0.08]" style={{ animationDelay: "-7s" }} />
        <div className="fx-orb h-[320px] w-[320px] left-[40%] top-[65%] bg-[#A78BFA]/[0.06]" style={{ animationDelay: "-12s" }} />
      </div>
      <div className="fx-grid pointer-events-none fixed inset-0 h-[55vh] opacity-60" aria-hidden="true" />

      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-[1440px] flex-col md:flex-row">
        <Sidebar activeView={activeView} onExitToLanding={onExitToLanding} onNavigate={onNavigate} />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar
            searchLabel={searchLabels[activeView] ?? "Buscar"}
            searchPlaceholder={searchPlaceholders[activeView] ?? "Buscar..."}
            subtitle={subtitle}
            title={title}
          />
          <main className="min-w-0 flex-1 px-4 pb-6 pt-4 sm:px-5 lg:px-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
