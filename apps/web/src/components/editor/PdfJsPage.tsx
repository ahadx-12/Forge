"use client";

import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { GlobalWorkerOptions, Util } from "pdfjs-dist";
import type { PDFDocumentProxy, TextItem } from "pdfjs-dist/types/src/display/api";

import type { ForgeManifestElement, ForgeOverlayEntry, ForgeOverlayMask } from "@/lib/api";
import { getPdfWorkerSrc } from "@/lib/pdfjs";
import { normalizedToPixelRect } from "@/components/editor/pageCanvas";
import {
  buildContentHash,
  buildElementId,
  hitTestSmallest,
  normalizeBbox,
  type PdfJsNormalizedBbox,
  type PdfJsRect,
  roundTo
} from "@/components/editor/pdfJsGeometry";

const DEBUG_OVERLAY_LIMIT = 60;

type PdfJsTextItem = {
  element_id: string;
  text: string;
  bbox: PdfJsNormalizedBbox;
  rect: PdfJsRect;
  fontSizePx: number;
  fontFamily: string;
  content_hash: string;
  element_type: "text";
  style?: ForgeManifestElement["style"];
};

export type PdfJsSelectionItem = Pick<
  PdfJsTextItem,
  "element_id" | "text" | "bbox" | "element_type" | "style" | "content_hash"
>;

type PdfJsPageProps = {
  pdfDocument: PDFDocumentProxy;
  pageIndex: number;
  overlayEntries?: Record<string, ForgeOverlayEntry>;
  overlayMasks?: ForgeOverlayMask[];
  selectedElementId?: string | null;
  showDebugOverlay?: boolean;
  onSelect: (item: PdfJsSelectionItem, overlayEntry?: ForgeOverlayEntry) => void;
};

const toTextItem = (item: unknown): item is TextItem =>
  Boolean(item && typeof item === "object" && "str" in item && "transform" in item);

function computeTextRect(item: TextItem, viewport: { transform: number[] }): PdfJsRect | null {
  const transformed = Util.transform(viewport.transform, item.transform);
  const [a, b, c, d, e, f] = transformed;
  const width = item.width ?? Math.hypot(a, b);
  const height = item.height ?? Math.hypot(c, d);
  if (!width || !height) {
    return null;
  }
  const x0 = e;
  const y0 = f;
  const x1 = e + a * width;
  const y1 = f + b * width;
  const x2 = e + c * height;
  const y2 = f + d * height;
  const x3 = x1 + c * height;
  const y3 = y1 + d * height;
  const left = Math.min(x0, x1, x2, x3);
  const right = Math.max(x0, x1, x2, x3);
  const top = Math.min(y0, y1, y2, y3);
  const bottom = Math.max(y0, y1, y2, y3);
  return {
    left,
    top,
    width: Math.max(0, right - left),
    height: Math.max(0, bottom - top)
  };
}

const HIT_SLOP_PX = 3;

export function PdfJsPage({
  pdfDocument,
  pageIndex,
  overlayEntries,
  overlayMasks,
  selectedElementId,
  showDebugOverlay,
  onSelect
}: PdfJsPageProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [viewportSize, setViewportSize] = useState({ width: 0, height: 0, scale: 1 });
  const [textItems, setTextItems] = useState<PdfJsTextItem[]>([]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      GlobalWorkerOptions.workerSrc = getPdfWorkerSrc();
    }
  }, []);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return;
    }
    const updateSize = () => setContainerWidth(element.clientWidth);
    const observer = new ResizeObserver(updateSize);
    observer.observe(element);
    updateSize();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;
    let renderTask: { cancel?: () => void } | null = null;

    async function renderPage() {
      const page = await pdfDocument.getPage(pageIndex + 1);
      const baseViewport = page.getViewport({ scale: 1 });
      const scale = containerWidth ? containerWidth / baseViewport.width : 1;
      const viewport = page.getViewport({ scale });
      if (cancelled) {
        return;
      }
      setViewportSize({ width: viewport.width, height: viewport.height, scale });
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext("2d");
        const outputScale = window.devicePixelRatio || 1;
        const renderViewport = page.getViewport({ scale: scale * outputScale });
        canvas.width = Math.floor(renderViewport.width);
        canvas.height = Math.floor(renderViewport.height);
        canvas.style.width = `${viewport.width}px`;
        canvas.style.height = `${viewport.height}px`;
        if (ctx) {
          const task = page.render({ canvasContext: ctx, viewport: renderViewport });
          renderTask = task;
          await task.promise;
        }
      }
      if (cancelled) {
        return;
      }
      const textContent = await page.getTextContent();
      if (cancelled) {
        return;
      }
      const items = textContent.items
        .filter(toTextItem)
        .map((item) => {
          const text = item.str ?? "";
          if (!text.trim()) {
            return null;
          }
          const rectBase = computeTextRect(item, baseViewport);
          const rect = computeTextRect(item, viewport);
          if (
            !rectBase ||
            rectBase.width <= 0 ||
            rectBase.height <= 0 ||
            !rect ||
            rect.width <= 0 ||
            rect.height <= 0
          ) {
            return null;
          }
          const bbox = normalizeBbox(rectBase, baseViewport.width, baseViewport.height);
          const fontSizePx = Math.abs(Math.hypot(item.transform[2], item.transform[3]) * viewport.scale);
          const fontSizePt = roundTo(fontSizePx / Math.max(scale, 0.01), 2);
          const fontFamily = item.fontName ?? "";
          const styleKey = [fontFamily, fontSizePt ? fontSizePt.toString() : ""].filter(Boolean).join("|");
          const element_id = buildElementId(pageIndex, text, bbox, styleKey);
          const content_hash = buildContentHash(text, bbox, styleKey);
          return {
            element_id,
            text,
            bbox,
            rect,
            fontSizePx,
            fontFamily,
            content_hash,
            element_type: "text",
            style: {
              font_size_pt: fontSizePt,
              font_family: fontFamily,
              is_bold: false,
              is_italic: false,
              color: "#000"
            }
          } satisfies PdfJsTextItem;
        })
        .filter(Boolean) as PdfJsTextItem[];
      setTextItems(items);
    }

    if (containerWidth > 0) {
      void renderPage();
    }

    return () => {
      cancelled = true;
      try {
        renderTask?.cancel?.();
      } catch {
        // ignore
      }
    };
  }, [containerWidth, pageIndex, pdfDocument]);

  const overlayEntriesMap = overlayEntries ?? {};
  const masksById = useMemo(() => {
    const map = new Map<string, ForgeOverlayMask>();
    overlayMasks?.forEach((mask) => {
      if (mask.element_id) {
        map.set(mask.element_id, mask);
      }
    });
    return map;
  }, [overlayMasks]);

  const textItemById = useMemo(() => {
    const map = new Map<string, PdfJsTextItem>();
    textItems.forEach((item) => map.set(item.element_id, item));
    return map;
  }, [textItems]);

  const handleClick = (event: MouseEvent<HTMLDivElement>) => {
    if (!textItems.length || !viewportSize.width || !viewportSize.height) {
      return;
    }
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width;
    const y = (event.clientY - bounds.top) / bounds.height;
    const slopX = HIT_SLOP_PX / viewportSize.width;
    const slopY = HIT_SLOP_PX / viewportSize.height;
    const hitIndex = hitTestSmallest(textItems, { x, y }, { x: slopX, y: slopY });
    if (hitIndex === null) {
      return;
    }
    const item = textItems[hitIndex];
    onSelect(item, overlayEntriesMap[item.element_id]);
  };

  return (
    <div ref={containerRef} className="w-full" data-page-index={pageIndex}>
      <div
        className="relative mx-auto max-w-full rounded-lg bg-white shadow-xl"
        style={{
          width: viewportSize.width,
          height: viewportSize.height
        }}
      >
        <canvas ref={canvasRef} className="block" />

        <div className="absolute inset-0 pointer-events-none">
          {Array.from(masksById.values()).map((mask) => {
            const rect = normalizedToPixelRect(mask.bbox as [number, number, number, number], viewportSize);
            return (
              <div
                key={`mask_${mask.element_id}`}
                style={{
                  position: "absolute",
                  left: rect.left,
                  top: rect.top,
                  width: rect.width,
                  height: rect.height,
                  backgroundColor: mask.color,
                  pointerEvents: "none"
                }}
              />
            );
          })}
          {Array.from(masksById.entries()).map(([elementId, mask]) => {
            const overlayEntry = overlayEntriesMap[elementId];
            if (!overlayEntry) {
              return null;
            }
            const rect = normalizedToPixelRect(mask.bbox as [number, number, number, number], viewportSize);
            const textItem = textItemById.get(elementId);
            const fontSize = textItem?.fontSizePx ?? Math.max(10, rect.height * 0.6);
            const fontFamily = textItem?.fontFamily;
            return (
              <div
                key={`overlay_${elementId}`}
                style={{
                  position: "absolute",
                  left: rect.left,
                  top: rect.top,
                  width: rect.width,
                  height: rect.height,
                  color: "#000",
                  fontSize,
                  fontFamily,
                  whiteSpace: "pre-wrap",
                  lineHeight: 1.2,
                  pointerEvents: "none"
                }}
              >
                {overlayEntry.text}
              </div>
            );
          })}
        </div>

        <div className="absolute inset-0 cursor-pointer" onClick={handleClick}>
          {textItems.map((item) => {
            const isSelected = selectedElementId === item.element_id;
            return (
              <div
                key={item.element_id}
                className={`absolute pointer-events-none transition-all duration-150 ${
                  isSelected
                    ? "ring-2 ring-blue-500 bg-blue-500/10 z-20"
                    : "hover:ring-1 hover:ring-blue-300/50 hover:bg-blue-300/5"
                }`}
                style={{
                  left: item.rect.left,
                  top: item.rect.top,
                  width: item.rect.width,
                  height: item.rect.height
                }}
              >
                <span
                  style={{
                    color: "transparent",
                    fontSize: item.fontSizePx,
                    fontFamily: item.fontFamily,
                    lineHeight: 1,
                    userSelect: "text"
                  }}
                >
                  {item.text}
                </span>
              </div>
            );
          })}

          {showDebugOverlay
            ? textItems.slice(0, DEBUG_OVERLAY_LIMIT).map((item) => (
                <div
                  key={`debug_${item.element_id}`}
                  style={{
                    position: "absolute",
                    left: item.rect.left,
                    top: item.rect.top,
                    width: item.rect.width,
                    height: item.rect.height,
                    border: "1px solid yellow",
                    pointerEvents: "none"
                  }}
                >
                  <span className="text-xs bg-yellow-500/50 px-1">{item.element_id}</span>
                </div>
              ))
            : null}
        </div>
      </div>
    </div>
  );
}
