"use client";

import { useState } from "react";
import { MessageSquareText, Send } from "lucide-react";

import { useSelectionStore } from "@/lib/state/store";

interface ChatDockProps {
  docId: string;
}

export function ChatDock({ docId }: ChatDockProps) {
  const [instruction, setInstruction] = useState("");
  const [error, setError] = useState<string | null>(null);
  const proposePatch = useSelectionStore((state) => state.proposePatch);
  const pendingProposal = useSelectionStore((state) => state.pendingProposal);
  const clearProposal = useSelectionStore((state) => state.clearProposal);
  const applyProposal = useSelectionStore((state) => state.applyProposal);

  const handlePlan = async () => {
    setError(null);
    try {
      await proposePatch(docId, instruction.trim());
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleApply = async () => {
    await applyProposal(docId);
  };

  return (
    <div className="rounded-2xl border border-forge-border bg-forge-card/60 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
        <MessageSquareText className="h-4 w-4 text-forge-accent-soft" />
        ChatDock
      </div>
      <p className="mt-2 text-xs text-slate-400">
        Describe the change you want. The assistant will draft a patch for your selected element.
      </p>
      <div className="mt-4 flex flex-col gap-2">
        <textarea
          className="min-h-[80px] w-full rounded-xl border border-forge-border bg-forge-panel/60 p-2 text-xs text-slate-200"
          placeholder="e.g., Make this line thicker and blue"
          value={instruction}
          onChange={(event) => setInstruction(event.target.value)}
        />
        <button
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-forge-border bg-forge-card/70 px-3 py-2 text-xs text-slate-200"
          type="button"
          onClick={() => void handlePlan()}
          disabled={!instruction.trim()}
        >
          <Send className="h-3.5 w-3.5" />
          Plan patch
        </button>
        {error ? <p className="text-xs text-red-300">{error}</p> : null}
      </div>

      {pendingProposal ? (
        <div className="mt-4 rounded-xl border border-forge-border bg-forge-panel/60 p-3 text-xs text-slate-300">
          <p className="text-[11px] text-slate-400">Proposed changes</p>
          <ul className="mt-2 space-y-1">
            {pendingProposal.ops.map((op) => (
              <li key={`${op.op}-${op.target_id}`}>
                <span className="text-slate-400">{op.target_id.slice(0, 6)}:</span> {op.op}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] text-slate-400">{pendingProposal.rationale_short}</p>
          <div className="mt-3 flex gap-2">
            <button
              className="flex-1 rounded-lg border border-forge-border bg-forge-card/70 px-3 py-2 text-xs text-slate-200"
              type="button"
              onClick={() => void handleApply()}
            >
              Apply
            </button>
            <button
              className="flex-1 rounded-lg border border-forge-border bg-forge-panel/60 px-3 py-2 text-xs text-slate-300"
              type="button"
              onClick={clearProposal}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
