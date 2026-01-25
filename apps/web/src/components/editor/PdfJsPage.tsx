"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { GlobalWorkerOptions, Util } from "pdfjs-dist";
import type { PDFDocumentProxy, TextItem } from "pdfjs-dist/types/src/display/api";

import type { DecodedPageV1, ForgeManifestElement, ForgeOverlayEntry, ForgeOverlayMask } from "@/lib/api";
import { getPdfWorkerSrc } from "@/lib/pdfjs";
import { normalizedToPixelRect } from "@/components/editor/pageCanvas";
import { RegionSelectLayer } from "@/components/editor/RegionSelectLayer";
import {
  buildContentHash,
  buildElementId,
  normalizeBbox,
  type PdfJsNormalizedBbox,
  type PdfJsRect,
  roundTo
} from "@/components/editor/pdfJsGeometry";
import {
  buildPdfJsFontMap,
  getPdfJsFontFamily,
  normalizePdfJsTextTransform,
  type PdfJsFontMap
} from "@/components/editor/pdfTextRender";

const DEBUG_OVERLAY_LIMIT = 60;

type PdfJsTextItem = {
  element_id: string;
  text: string;
  bbox: PdfJsNormalizedBbox;
  rect: PdfJsRect;
  fontSizePx: number;
  fontFamily: string | null;
  fontName: string | null;
  fontSizePxAtScale1: number;
  transform: [number, number, number, number, number, number];
  content_hash: string;
  element_type: "text";
  style?: ForgeManifestElement["style"];
};

type PdfJsPageProps = {
  pdfDocument: PDFDocumentProxy;
  pageIndex: number;
  overlayEntries?: Record<string, ForgeOverlayEntry>;
  overlayMasks?: ForgeOverlayMask[];
  showDebugOverlay?: boolean;
  decodedPage?: DecodedPageV1 | null;
  selectedDecodedIds?: string[];
  onRegionSelect?: (
    pageIndex: number,
    bbox: [number, number, number, number],
    viewportSize: { width: number; height: number }
  ) => void;
  onFontMapUpdate?: (pageIndex: number, fontMap: PdfJsFontMap) => void;
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

export function PdfJsPage({
  pdfDocument,
  pageIndex,
  overlayEntries,
  overlayMasks,
  showDebugOverlay,
  decodedPage,
  selectedDecodedIds,
  onRegionSelect,
  onFontMapUpdate
}: PdfJsPageProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const onFontMapUpdateRef = useRef<typeof onFontMapUpdate>(onFontMapUpdate);
  onFontMapUpdateRef.current = onFontMapUpdate;
  const [containerWidth, setContainerWidth] = useState(0);
  const [viewportSize, setViewportSize] = useState({ width: 0, height: 0, scale: 1 });
  const [textItems, setTextItems] = useState<PdfJsTextItem[]>([]);
  const [pdfFontMap, setPdfFontMap] = useState<PdfJsFontMap>({});

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
      const nextFontMap = buildPdfJsFontMap(textContent.styles as Record<string, { fontFamily?: string }>);
      setPdfFontMap(nextFontMap);
      onFontMapUpdateRef.current?.(pageIndex, nextFontMap);
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
          const baseTransform = Util.transform(baseViewport.transform, item.transform);
          const viewportTransform = Util.transform(viewport.transform, item.transform);
          const normalizedTransform = normalizePdfJsTextTransform(viewportTransform);
          if (!normalizedTransform) {
            return null;
          }
          const bbox = normalizeBbox(rectBase, baseViewport.width, baseViewport.height);
          const fontSizePxAtScale1 =
            normalizePdfJsTextTransform(baseTransform)?.fontSizePx ?? Math.max(0, Math.hypot(item.transform[2], item.transform[3]));
          const fontSizePx = normalizedTransform.fontSizePx;
          const fontSizePt = roundTo(fontSizePx / Math.max(scale, 0.01), 2);
          const fontName = item.fontName ?? null;
          const fontFamily = getPdfJsFontFamily(fontName, nextFontMap);
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
            fontName,
            fontSizePxAtScale1,
            transform: normalizedTransform.matrix,
            content_hash,
            element_type: "text",
            style: {
              font_size_pt: fontSizePt,
              font_family: fontFamily ?? fontName ?? "",
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

  const selectedDecodedSet = useMemo(() => new Set(selectedDecodedIds ?? []), [selectedDecodedIds]);

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
          {decodedPage
            ? decodedPage.elements.map((element) => {
                if (!selectedDecodedSet.has(element.id)) {
                  return null;
                }
                const rect = normalizedToPixelRect(element.bbox_norm, viewportSize);
                return (
                  <div
                    key={`decoded_${element.id}`}
                    className="absolute rounded-md ring-2 ring-blue-500/80 bg-blue-500/10"
                    style={{
                      left: rect.left,
                      top: rect.top,
                      width: rect.width,
                      height: rect.height
                    }}
                  />
                );
              })
            : null}
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
            const fontFamily =
              textItem?.fontFamily ??
              (textItem?.fontName ? getPdfJsFontFamily(textItem.fontName, pdfFontMap) : null) ??
              "Helvetica, Arial, sans-serif";
            const transform = textItem?.transform ?? [1, 0, 0, 1, rect.left, rect.top];
            return (
              <div
                key={`overlay_${elementId}`}
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  width: rect.width,
                  height: rect.height,
                  color: "#000",
                  fontSize,
                  fontFamily,
                  whiteSpace: "pre",
                  lineHeight: 1,
                  pointerEvents: "none",
                  transform: `matrix(${transform.join(",")})`,
                  transformOrigin: "0 0"
                }}
              >
                {overlayEntry.text}
              </div>
            );
          })}
        </div>

        <div className="absolute inset-0 pointer-events-none">
          {textItems.map((item) => (
            <div
              key={item.element_id}
              className="absolute pointer-events-none transition-all duration-150 hover:ring-1 hover:ring-blue-300/50 hover:bg-blue-300/5"
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
                      fontFamily: item.fontFamily ?? "inherit",
                      lineHeight: 1,
                      userSelect: "text"
                    }}
                  >
                {item.text}
              </span>
            </div>
          ))}

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

        {onRegionSelect && viewportSize.width && viewportSize.height ? (
          <RegionSelectLayer
            width={viewportSize.width}
            height={viewportSize.height}
            onSelect={(bbox) => onRegionSelect(pageIndex, bbox, viewportSize)}
          />
        ) : null}
      </div>
    </div>
  );
}
