"use client";

import { useMemo, useState } from "react";

import { useSelectionStore } from "@/lib/state/store";

const DEFAULT_OPACITY = 1;

function toHex(color?: unknown): string {
  if (!Array.isArray(color)) {
    return "#000000";
  }
  const [r, g, b] = color;
  const toByte = (value: number) => Math.round(Math.min(1, Math.max(0, value)) * 255);
  return `#${toByte(r).toString(16).padStart(2, "0")}${toByte(g)
    .toString(16)
    .padStart(2, "0")}${toByte(b).toString(16).padStart(2, "0")}`;
}

function fromHex(hex: string): number[] {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16) / 255;
  const g = parseInt(clean.slice(2, 4), 16) / 255;
  const b = parseInt(clean.slice(4, 6), 16) / 255;
  return [r, g, b];
}

export function InspectorPanel({ docId }: { docId: string }) {
  const { irPages, selectedId, activePageIndex, commitManualPatch } = useSelectionStore((state) => ({
    irPages: state.irPages,
    selectedId: state.selectedId,
    activePageIndex: state.activePageIndex,
    commitManualPatch: state.commitManualPatch
  }));
  const [pathColor, setPathColor] = useState("#0f172a");
  const [pathWidth, setPathWidth] = useState(1);
  const [pathOpacity, setPathOpacity] = useState(DEFAULT_OPACITY);
  const [textValue, setTextValue] = useState("");
  const [textPolicy, setTextPolicy] = useState<"FIT_IN_BOX" | "OVERFLOW_NOTICE">("FIT_IN_BOX");

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

  const pageIndex = activePageIndex ?? 0;

  const syncFields = () => {
    if (!selectedPrimitive) {
      return;
    }
    if (selectedPrimitive.kind === "path") {
      setPathColor(toHex(selectedPrimitive.style.stroke_color ?? [0, 0, 0]));
      setPathWidth(Number(selectedPrimitive.style.stroke_width ?? 1));
      setPathOpacity(Number(selectedPrimitive.style.opacity ?? DEFAULT_OPACITY));
    } else if (selectedPrimitive.kind === "text") {
      setTextValue(selectedPrimitive.text ?? "");
      setTextPolicy("FIT_IN_BOX");
    }
  };

  const handleApplyPath = async () => {
    if (!selectedPrimitive || selectedPrimitive.kind !== "path") {
      return;
    }
    await commitManualPatch(docId, {
      page_index: pageIndex,
      selected_ids: [selectedPrimitive.id],
      ops: [
        {
          op: "set_style",
          target_id: selectedPrimitive.id,
          stroke_color: fromHex(pathColor),
          stroke_width_pt: pathWidth,
          opacity: pathOpacity
        }
      ],
      rationale_short: "Manual style change"
    });
  };

  const handleApplyText = async () => {
    if (!selectedPrimitive || selectedPrimitive.kind !== "text") {
      return;
    }
    await commitManualPatch(docId, {
      page_index: pageIndex,
      selected_ids: [selectedPrimitive.id],
      ops: [
        {
          op: "replace_text",
          target_id: selectedPrimitive.id,
          new_text: textValue,
          policy: textPolicy
        }
      ],
      rationale_short: "Manual text update"
    });
  };

  return (
    <div className="rounded-2xl border border-forge-border bg-forge-card/60 p-4">
      <h3 className="text-sm font-semibold text-slate-200">Inspector</h3>
      {selectedPrimitive ? (
        <div className="mt-3 space-y-4 text-xs text-slate-300">
          <div className="space-y-2">
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
          </div>

          {selectedPrimitive.kind === "path" ? (
            <div className="space-y-3 rounded-xl border border-forge-border bg-forge-panel/60 p-3">
              <div>
                <label className="text-[11px] text-slate-400">Stroke color</label>
                <input
                  className="mt-1 h-8 w-full rounded border border-forge-border bg-transparent"
                  type="color"
                  value={pathColor}
                  onChange={(event) => setPathColor(event.target.value)}
                  onFocus={syncFields}
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-400">Stroke width (pt)</label>
                <input
                  className="mt-1 w-full rounded border border-forge-border bg-forge-card/40 px-2 py-1 text-xs text-slate-200"
                  type="number"
                  min={0}
                  step={0.5}
                  value={pathWidth}
                  onChange={(event) => setPathWidth(Number(event.target.value))}
                  onFocus={syncFields}
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-400">Opacity</label>
                <input
                  className="mt-2 w-full"
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={pathOpacity}
                  onChange={(event) => setPathOpacity(Number(event.target.value))}
                  onFocus={syncFields}
                />
              </div>
              <button
                className="w-full rounded-lg border border-forge-border bg-forge-card/70 px-3 py-2 text-xs text-slate-200"
                type="button"
                onClick={() => void handleApplyPath()}
              >
                Apply style
              </button>
            </div>
          ) : null}

          {selectedPrimitive.kind === "text" ? (
            <div className="space-y-3 rounded-xl border border-forge-border bg-forge-panel/60 p-3">
              <div>
                <label className="text-[11px] text-slate-400">Text</label>
                <textarea
                  className="mt-1 w-full rounded border border-forge-border bg-forge-card/40 px-2 py-1 text-xs text-slate-200"
                  rows={3}
                  value={textValue}
                  onChange={(event) => setTextValue(event.target.value)}
                  onFocus={syncFields}
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-400">Policy</label>
                <select
                  className="mt-1 w-full rounded border border-forge-border bg-forge-card/40 px-2 py-1 text-xs text-slate-200"
                  value={textPolicy}
                  onChange={(event) => setTextPolicy(event.target.value as "FIT_IN_BOX" | "OVERFLOW_NOTICE")}
                  onFocus={syncFields}
                >
                  <option value="FIT_IN_BOX">Fit in box</option>
                  <option value="OVERFLOW_NOTICE">Overflow notice</option>
                </select>
              </div>
              <button
                className="w-full rounded-lg border border-forge-border bg-forge-card/70 px-3 py-2 text-xs text-slate-200"
                type="button"
                onClick={() => void handleApplyText()}
              >
                Apply text change
              </button>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="mt-3 text-xs text-slate-400">
          Click or box-select a primitive to inspect its properties.
        </div>
      )}
    </div>
  );
}
