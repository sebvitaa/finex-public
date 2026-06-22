import type { ReactNode } from "react";

type EmptyStateProps = {
  title: string;
  body: string;
  action?: ReactNode;
};

export function EmptyState({ title, body, action }: EmptyStateProps) {
  return (
    <div className="panel-tight flex min-h-48 flex-col items-center justify-center px-4 py-8 text-center">
      <p className="text-sm font-semibold text-text">{title}</p>
      <p className="mt-2 max-w-sm text-sm text-muted">{body}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
