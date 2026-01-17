"use client";

import { MessageSquareText } from "lucide-react";

export function ChatDock() {
  return (
    <div className="rounded-2xl border border-forge-border bg-forge-card/60 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
        <MessageSquareText className="h-4 w-4 text-forge-accent-soft" />
        ChatDock
      </div>
      <p className="mt-2 text-xs text-slate-400">
        Assistant insights will appear here in Week 2. For now, this dock keeps your place for
        annotations, prompts, and suggestions.
      </p>
      <div className="mt-4 rounded-xl border border-forge-border bg-forge-panel/60 p-3 text-xs text-slate-500">
        Start a conversation after uploading a document.
      </div>
    </div>
  );
}
