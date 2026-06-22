import { X } from "lucide-react";
import type { PropsWithChildren } from "react";

type DrawerProps = PropsWithChildren<{
  open: boolean;
  title: string;
  onClose: () => void;
}>;

export function Drawer({ children, onClose, open, title }: DrawerProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40 bg-black/60" role="presentation">
      <aside className="ml-auto h-full w-full max-w-3xl overflow-y-auto border-l border-border bg-surface p-4 shadow-panel" role="dialog">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold">{title}</h2>
          <button className="focus-ring rounded-[8px] border border-border p-2 text-muted hover:text-text" onClick={onClose} type="button">
            <X aria-label="Cerrar" className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-4">{children}</div>
      </aside>
    </div>
  );
}
