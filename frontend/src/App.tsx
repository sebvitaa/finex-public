import { useState } from "react";

import { AppShell } from "./components/layout/AppShell";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import { ImportPage } from "./features/import/ImportPage";
import { LandingPage } from "./features/landing/LandingPage";
import { ManualPage } from "./features/manual/ManualPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { useSession } from "./lib/sessionContext";

const viewTitles: Record<string, { title: string; subtitle: string }> = {
  dashboard: { title: "Dashboard financiero", subtitle: "Resumen" },
  movements: { title: "Movimientos", subtitle: "Registrar y revisar" },
  obligations: { title: "Obligaciones", subtitle: "Cobrar y pagar" },
  import: { title: "Importar correos", subtitle: "Gmail y texto" },
  mailbox: { title: "Revisar correos", subtitle: "Candidatos y bandeja" },
  accounts: { title: "Cuentas e inversiones", subtitle: "Saldos y patrimonio" },
  settings: { title: "Configuracion", subtitle: "Administracion y privacidad" }
};

export function App() {
  const [activeView, setActiveView] = useState("dashboard");
  // In production we open the app directly so the public QR lands on the dashboard.
  // The landing remains available as an exit target and in tests/local dev.
  const [entered, setEntered] = useState(() => import.meta.env.MODE === "test" || import.meta.env.PROD);
  const { setSession } = useSession();
  const current = viewTitles[activeView] ?? viewTitles.dashboard;

  if (!entered) {
    return (
      <LandingPage
        onEnter={() => setEntered(true)}
        onExploreDemo={() => {
          setSession("demo");
          setActiveView("dashboard");
          setEntered(true);
        }}
      />
    );
  }

  return (
    <AppShell activeView={activeView} onExitToLanding={() => setEntered(false)} onNavigate={setActiveView} subtitle={current.subtitle} title={current.title}>
      {activeView === "dashboard" ? <DashboardPage /> : null}
      {activeView === "movements" ? <ManualPage mode="movements" /> : null}
      {activeView === "obligations" ? <ManualPage mode="obligations" /> : null}
      {activeView === "import" ? <ImportPage mode="import" /> : null}
      {activeView === "mailbox" ? <ImportPage mode="review" /> : null}
      {activeView === "accounts" ? <SettingsPage mode="accounts" /> : null}
      {activeView === "settings" ? <SettingsPage mode="settings" /> : null}
    </AppShell>
  );
}
