import type { ReactNode } from "react";

import { formatCurrency } from "../../lib/format";
import { cardToneStyles, ColorCard, type CardTone } from "./ColorCard";

type MetricCardProps = {
  label: string;
  value: number;
  delta: string;
  tone?: CardTone;
  format?: "currency" | "number";
  icon?: ReactNode;
};

export function MetricCard({ label, value, delta, format = "currency", tone = "accent", icon }: MetricCardProps) {
  const style = cardToneStyles[tone];
  return (
    <ColorCard hover tone={tone} className="p-4">
      <section>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm text-muted">{label}</p>
            <p className="mt-2 break-words text-2xl font-semibold leading-tight tracking-normal tabular-nums">
              {format === "currency" ? formatCurrency(value) : value}
            </p>
          </div>
          {icon ? <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-[9px] border ${style.chip}`}>{icon}</div> : null}
        </div>
        <p className={`mt-3 text-xs ${style.accentText}`}>{delta}</p>
      </section>
    </ColorCard>
  );
}
