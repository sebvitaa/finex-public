import type { ReactNode } from "react";

export type CardTone = "accent" | "danger" | "warning" | "info" | "violet" | "neutral";

type ToneStyle = {
  border: string;
  gradient: string;
  glow: string;
  chip: string;
  accentText: string;
  bar: string;
};

/**
 * Static Tailwind class strings per tone. They must be literal (no string
 * interpolation of color names) so Tailwind's JIT keeps them in the build.
 */
export const cardToneStyles: Record<CardTone, ToneStyle> = {
  accent: {
    border: "border-accent/30",
    gradient: "from-accent/15",
    glow: "bg-accent/20",
    chip: "border-accent/30 bg-accent/15 text-accent",
    accentText: "text-accent",
    bar: "bg-accent"
  },
  danger: {
    border: "border-danger/30",
    gradient: "from-danger/15",
    glow: "bg-danger/20",
    chip: "border-danger/30 bg-danger/15 text-danger",
    accentText: "text-danger",
    bar: "bg-danger"
  },
  warning: {
    border: "border-warning/30",
    gradient: "from-warning/15",
    glow: "bg-warning/20",
    chip: "border-warning/30 bg-warning/15 text-warning",
    accentText: "text-warning",
    bar: "bg-warning"
  },
  info: {
    border: "border-info/30",
    gradient: "from-info/15",
    glow: "bg-info/20",
    chip: "border-info/30 bg-info/15 text-info",
    accentText: "text-info",
    bar: "bg-info"
  },
  violet: {
    border: "border-[#A78BFA]/30",
    gradient: "from-[#A78BFA]/15",
    glow: "bg-[#A78BFA]/20",
    chip: "border-[#A78BFA]/30 bg-[#A78BFA]/15 text-[#A78BFA]",
    accentText: "text-[#A78BFA]",
    bar: "bg-[#A78BFA]"
  },
  neutral: {
    border: "border-border",
    gradient: "from-white/[0.05]",
    glow: "bg-white/10",
    chip: "border-border bg-surface2 text-muted",
    accentText: "text-muted",
    bar: "bg-muted"
  }
};

/** Resolve a card tone from a card art variant, falling back to the account type. */
export function accountTone(variant?: string | null, accountType?: string | null): CardTone {
  switch ((variant ?? "").toLowerCase()) {
    case "green":
      return "accent";
    case "red":
      return "danger";
    case "blue":
      return "info";
    case "black":
      return "violet";
    case "white":
      return "neutral";
  }
  switch ((accountType ?? "").toLowerCase()) {
    case "checking":
      return "info";
    case "savings":
      return "accent";
    case "credit_card":
      return "violet";
    case "wallet":
    case "cash":
      return "warning";
    default:
      return "neutral";
  }
}

type ColorCardProps = {
  tone?: CardTone;
  className?: string;
  hover?: boolean;
  children: ReactNode;
};

/** Tinted, gradient surface with a soft corner glow — the app-wide colored card. */
export function ColorCard({ tone = "neutral", className = "", hover = false, children }: ColorCardProps) {
  const style = cardToneStyles[tone];
  return (
    <div className={`fx-card ${style.border} ${hover ? "fx-card-hover" : ""} bg-gradient-to-br ${style.gradient} to-surface ${className}`}>
      <div className={`pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full ${style.glow} blur-3xl`} aria-hidden="true" />
      <div className="relative">{children}</div>
    </div>
  );
}
