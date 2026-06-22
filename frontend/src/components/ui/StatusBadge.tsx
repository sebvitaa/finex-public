import type { TransactionStatus } from "../../types";

type StatusBadgeProps = {
  status: TransactionStatus;
};

const labels: Record<TransactionStatus, string> = {
  classified: "Clasificado",
  needs_review: "Por revisar",
  ignored: "Ignorado",
  duplicate: "Duplicado",
  pending_payment: "Pendiente",
  partially_paid: "Pago parcial",
  paid: "Pagado",
  overdue: "Vencido"
};

const classes: Record<TransactionStatus, string> = {
  classified: "border-accent/40 bg-accent/10 text-accent",
  needs_review: "border-warning/40 bg-warning/10 text-warning",
  ignored: "border-subtle/40 bg-surface2 text-muted",
  duplicate: "border-danger/40 bg-danger/10 text-danger",
  pending_payment: "border-warning/40 bg-warning/10 text-warning",
  partially_paid: "border-info/40 bg-info/10 text-info",
  paid: "border-accent/40 bg-accent/10 text-accent",
  overdue: "border-danger/40 bg-danger/10 text-danger"
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`inline-flex rounded-[8px] border px-2 py-1 text-xs ${classes[status]}`}>
      {labels[status]}
    </span>
  );
}
