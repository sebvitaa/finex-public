import { Bell, CircleCheck, FlaskConical, Search } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../../lib/api";
import { useSession } from "../../lib/sessionContext";
import type { BackendHealth } from "../../types";

type TopBarProps = {
  searchLabel?: string;
  searchPlaceholder?: string;
  title: string;
  subtitle?: string;
};

export function TopBar({ searchLabel = "Buscar", searchPlaceholder = "Buscar...", subtitle = "29 may 2026", title }: TopBarProps) {
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [isOffline, setIsOffline] = useState(false);
  const { isDemo } = useSession();

  useEffect(() => {
    let ignore = false;

    api
      .health()
      .then((data) => {
        if (!ignore) {
          setHealth(data);
          setIsOffline(false);
        }
      })
      .catch(() => {
        if (!ignore) {
          setIsOffline(true);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-bg/80 px-4 py-3 backdrop-blur-xl sm:px-5 lg:px-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase text-subtle">{subtitle}</p>
          <h1 className="text-lg font-semibold leading-tight">{title}</h1>
        </div>

        <div className="flex min-w-0 items-center gap-2">
          <label className="focus-within:ring-info flex min-w-0 flex-1 items-center gap-2 rounded-[8px] border border-border bg-surface px-3 py-2 text-sm text-muted focus-within:ring-2 sm:w-64 sm:flex-none">
            <Search aria-hidden="true" className="h-4 w-4 shrink-0" />
            <input
              aria-label={searchLabel}
              className="min-w-0 flex-1 bg-transparent text-text outline-none placeholder:text-subtle"
              placeholder={searchPlaceholder}
              type="search"
            />
          </label>

          <div className="hidden items-center gap-2 rounded-[8px] border border-border bg-surface px-3 py-2 text-xs text-muted sm:flex">
            <CircleCheck aria-hidden="true" className={`h-4 w-4 ${isOffline ? "text-warning" : "text-accent"}`} />
            <span>{isOffline ? "Backend offline" : `${health?.service ?? "finex"} OK`}</span>
          </div>

          {isDemo && (
            <div className="hidden items-center gap-1.5 rounded-[8px] border border-warning/40 bg-warning/10 px-3 py-2 text-xs font-medium text-warning sm:flex">
              <FlaskConical aria-hidden="true" className="h-3.5 w-3.5" />
              <span>Demo</span>
            </div>
          )}

          <button className="focus-ring rounded-[8px] border border-border bg-surface p-2 text-muted hover:text-text" type="button">
            <Bell aria-label="Notificaciones" className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
