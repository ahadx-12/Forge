"use client";

import { useMemo } from "react";

import { useSelectionStore } from "@/lib/state/store";

export function InspectorPanel() {
  const { irPages, selectedId } = useSelectionStore((state) => ({
    irPages: state.irPages,
    selectedId: state.selectedId
  }));

  const selectedPrimitive = useMemo(() => {
    if (!selectedId) {
      return null;
    }
    for (const page of Object.values(irPages)) {
      const match = page.primitives.find((primitive) => primitive.id === selectedId);
      if (match) {
        return match;
      }
    }
    return null;
  }, [irPages, selectedId]);

  return (
    <div className="rounded-2xl border border-forge-border bg-forge-card/60 p-4">
      <h3 className="text-sm font-semibold text-slate-200">Inspector</h3>
      {selectedPrimitive ? (
        <div className="mt-3 space-y-2 text-xs text-slate-300">
          <p>
            <span className="text-slate-400">ID:</span> {selectedPrimitive.id}
          </p>
          <p>
            <span className="text-slate-400">Kind:</span> {selectedPrimitive.kind}
          </p>
          <p>
            <span className="text-slate-400">BBox:</span>{" "}
            {selectedPrimitive.bbox.map((value) => value.toFixed(2)).join(", ")}
          </p>
          {selectedPrimitive.text ? (
            <p>
              <span className="text-slate-400">Text:</span> {selectedPrimitive.text}
            </p>
          ) : null}
          <div>
            <p className="text-slate-400">Style:</p>
            <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-forge-panel/60 p-2 text-[11px] text-slate-200">
              {JSON.stringify(selectedPrimitive.style, null, 2)}
            </pre>
          </div>
        </div>
      ) : (
        <div className="mt-3 text-xs text-slate-400">
          Click or box-select a primitive to inspect its properties.
        </div>
      )}
    </div>
  );
}
