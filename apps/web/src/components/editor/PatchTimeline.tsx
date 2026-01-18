"use client";

import { formatDistanceToNow } from "date-fns";
import { Eye, EyeOff, RotateCcw } from "lucide-react";

import { useSelectionStore } from "@/lib/state/store";

interface PatchTimelineProps {
  docId: string;
  pageIndex: number;
}

export function PatchTimeline({ docId, pageIndex }: PatchTimelineProps) {
  const patchsets = useSelectionStore((state) => state.patchsets);
  const patchVisibility = useSelectionStore((state) => state.patchVisibility);
  const togglePatchVisibility = useSelectionStore((state) => state.togglePatchVisibility);
  const undoLastPatch = useSelectionStore((state) => state.undoLastPatch);

  return (
    <div className="rounded-2xl border border-forge-border bg-forge-card/60 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Patch history</h3>
        <button
          className="inline-flex items-center gap-1 rounded-lg border border-forge-border bg-forge-panel/60 px-2 py-1 text-xs text-slate-200 transition hover:border-forge-accent/60"
          type="button"
          onClick={() => void undoLastPatch(docId)}
          disabled={!patchsets.length}
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Undo
        </button>
      </div>
      {patchsets.length === 0 ? (
        <p className="mt-3 text-xs text-slate-400">No patches yet. Apply a change to see it here.</p>
      ) : (
        <div className="mt-3 space-y-3">
          {patchsets.map((patchset) => {
            const isVisible = patchVisibility[patchset.patchset_id] ?? true;
            return (
              <div
                key={patchset.patchset_id}
                className="rounded-xl border border-forge-border bg-forge-panel/50 p-3 text-xs text-slate-300"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-100">Patch #{patchset.patchset_id.slice(0, 8)}</p>
                    <p className="text-[11px] text-slate-400">
                      {formatDistanceToNow(new Date(patchset.created_at_iso), { addSuffix: true })}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="rounded-md border border-forge-border bg-forge-card/60 p-1 text-slate-200"
                    onClick={() => void togglePatchVisibility(docId, pageIndex, patchset.patchset_id)}
                  >
                    {isVisible ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
                  </button>
                </div>
                {isVisible ? (
                  <>
                    <div className="mt-2 text-[11px] text-slate-400">
                      {patchset.rationale_short ?? "Manual edit"}
                    </div>
                    <ul className="mt-2 space-y-1 text-[11px] text-slate-300">
                      {patchset.diff_summary.map((entry) => (
                        <li key={`${patchset.patchset_id}-${entry.target_id}`}>
                          <span className="text-slate-400">{entry.target_id.slice(0, 6)}:</span>{" "}
                          {entry.changed_fields.join(", ")}
                        </li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <p className="mt-2 text-[11px] text-slate-500">Hidden in preview</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
