import { X } from "lucide-react";
import type { PropsWithChildren } from "react";

type ModalProps = PropsWithChildren<{
  open: boolean;
  title: string;
  onClose: () => void;
}>;

export function Modal({ children, onClose, open, title }: ModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="presentation">
      <section className="panel w-full max-w-2xl p-4" role="dialog">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold">{title}</h2>
          <button className="focus-ring rounded-[8px] border border-border p-2 text-muted hover:text-text" onClick={onClose} type="button">
            <X aria-label="Cerrar" className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-4">{children}</div>
      </section>
    </div>
  );
}
