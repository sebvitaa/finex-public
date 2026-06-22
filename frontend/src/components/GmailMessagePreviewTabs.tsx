import { useState } from "react";

import type { GmailMessage } from "../types";

type GmailMessagePreviewTabsProps = {
  message: GmailMessage;
};

type PreviewTab = "summary" | "full" | "html";

export function GmailMessagePreviewTabs({ message }: GmailMessagePreviewTabsProps) {
  const [activeTab, setActiveTab] = useState<PreviewTab>("summary");
  const preview = message.body_preview?.trim() || "";
  const fullText = message.body_text?.trim() || preview;
  const htmlPreview = message.body_html?.trim() || "";
  const hasHtmlPreview = htmlPreview.length > 0;

  return (
    <div className="mt-3">
      <div className="inline-flex rounded-[8px] border border-border bg-surface p-1 text-xs">
        <button
          className={`focus-ring rounded-[6px] px-3 py-1 ${activeTab === "summary" ? "bg-surface2 text-text" : "text-muted hover:text-text"}`}
          onClick={() => setActiveTab("summary")}
          type="button"
        >
          Resumen
        </button>
        <button
          className={`focus-ring rounded-[6px] px-3 py-1 ${activeTab === "full" ? "bg-surface2 text-text" : "text-muted hover:text-text"}`}
          onClick={() => setActiveTab("full")}
          type="button"
        >
          Completo
        </button>
        {hasHtmlPreview ? (
          <button
            className={`focus-ring rounded-[6px] px-3 py-1 ${activeTab === "html" ? "bg-surface2 text-text" : "text-muted hover:text-text"}`}
            onClick={() => setActiveTab("html")}
            type="button"
          >
            HTML
          </button>
        ) : null}
      </div>

      {activeTab === "summary" ? (
        <p className="mt-3 line-clamp-4 text-sm leading-6 text-muted">{preview || "Sin preview guardada."}</p>
      ) : activeTab === "html" && hasHtmlPreview ? (
        <div className="mt-3 overflow-hidden rounded-[8px] border border-border bg-white">
          <iframe
            className="h-96 w-full bg-white"
            referrerPolicy="no-referrer"
            sandbox=""
            srcDoc={htmlPreview}
            title={`HTML de ${message.subject}`}
          />
        </div>
      ) : (
        <div className="mt-3 rounded-[8px] border border-border bg-surface p-3">
          <p className="text-xs uppercase tracking-wide text-subtle">Texto completo guardado</p>
          <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs leading-5 text-muted">
            {fullText || "Sin cuerpo guardado para este correo."}
          </pre>
        </div>
      )}
    </div>
  );
}
