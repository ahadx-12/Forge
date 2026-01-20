"use client";

import React from "react";

import type { ForgeManifestItem, ForgeOverlayEntry, ForgeOverlayMask } from "@/lib/api";

const DEFAULT_FONT_SIZE = 10;

interface OverlayLayerStackProps {
  pageIndex: number;
  items: ForgeManifestItem[];
  overlayMap: Record<string, ForgeOverlayEntry>;
  masks: ForgeOverlayMask[];
  selectedForgeId?: string | null;
  showDebugOverlay?: boolean;
  debugLimit?: number;
  onSelect: (pageIndex: number, item: ForgeManifestItem, overlayEntry?: ForgeOverlayEntry) => void;
}

export function OverlayLayerStack({
  pageIndex,
  items,
  overlayMap,
  masks,
  selectedForgeId,
  showDebugOverlay = false,
  debugLimit = 0,
  onSelect
}: OverlayLayerStackProps) {
  return (
    <>
      <div className="absolute inset-0 pointer-events-none" data-layer="masks">
        {masks.map((mask, index) => {
          const [x0, y0, x1, y1] = mask.bbox_px;
          return (
            <div
              key={`mask_${pageIndex}_${index}`}
              className="absolute"
              style={{
                left: x0,
                top: y0,
                width: x1 - x0,
                height: y1 - y0,
                backgroundColor: mask.color
              }}
            />
          );
        })}
      </div>
      <div className="absolute inset-0" data-layer="text">
        {items.map((item) => {
          const overlayEntry = overlayMap[item.forge_id];
          const displayText = overlayEntry?.text ?? item.text;
          const isSelected = selectedForgeId === item.forge_id;
          const [x0, y0, x1, y1] = item.bbox;
          const width = x1 - x0;
          const height = y1 - y0;
          const fontSize = item.size || DEFAULT_FONT_SIZE;
          const estimatedTextWidth = displayText.length * fontSize * 0.6;
          const isLikelyOverflowing = estimatedTextWidth > width;
          return (
            <div
              key={item.forge_id}
              role="button"
              tabIndex={0}
              onClick={() => onSelect(pageIndex, item, overlayEntry)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  onSelect(pageIndex, item, overlayEntry);
                }
              }}
              className={`absolute cursor-pointer select-none rounded-sm px-0.5 leading-none ${
                isSelected ? "ring-2 ring-forge-accent" : "hover:ring-1 hover:ring-forge-accent/50"
              }`}
              style={{
                left: x0,
                top: y0,
                width,
                height,
                color: item.color,
                fontSize,
                fontFamily: "Helvetica, Arial, sans-serif",
                lineHeight: 1.2,
                whiteSpace: "nowrap",
                overflow: "visible",
                textOverflow: "clip",
                transformOrigin: "top left",
                pointerEvents: "auto",
                ...(showDebugOverlay
                  ? {
                      outline: `1px solid ${
                        isLikelyOverflowing ? "rgba(255,0,0,0.6)" : "rgba(255,0,0,0.3)"
                      }`
                    }
                  : {})
              }}
            >
              {displayText}
            </div>
          );
        })}
      </div>
      {showDebugOverlay ? (
        <div className="absolute inset-0 pointer-events-none" data-layer="debug">
          {items.slice(0, debugLimit).map((item) => {
            const [x0, y0, x1, y1] = item.bbox;
            const width = x1 - x0;
            const height = y1 - y0;
            return (
              <div
                key={`debug_${item.forge_id}`}
                className="absolute border border-amber-400/80 text-[10px] text-amber-200"
                style={{
                  left: x0,
                  top: y0,
                  width,
                  height
                }}
              >
                <span className="absolute -top-4 left-0 rounded bg-amber-500/20 px-1">
                  {item.forge_id} w:{Math.round(width)} h:{Math.round(height)} len:{item.text.length}
                </span>
              </div>
            );
          })}
        </div>
      ) : null}
    </>
  );
}
