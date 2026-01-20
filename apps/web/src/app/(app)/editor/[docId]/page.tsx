"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { FileText, MessageSquareText, Send } from "lucide-react";

import {
  apiUrl,
  commitOverlayPatch,
  exportPdfUrl,
  getDocumentMeta,
  getForgeManifest,
  getForgeOverlay,
  planOverlayPatch,
  type ExportMaskMode,
  type ForgeManifest,
  type ForgeManifestElement,
  type ForgeOverlayEntry,
  type ForgeOverlayMask,
  type ForgeOverlayPlanResponse,
  type ForgeOverlaySelection
} from "@/lib/api";
import { createBBoxConverter, type BBox } from "@/components/editor/overlayGeometry";

type SelectedOverlay = {
  page_index: number;
  element_id: string;
  text: string;
  bbox: number[];
  content_hash: string;
  element_type: ForgeManifestElement["element_type"];
  style: ForgeManifestElement["style"];
};

type OverlayPageState = {
  entries: Record<string, ForgeOverlayEntry>;
  masks: ForgeOverlayMask[];
  pageImageWidthPx?: number;
  pageImageHeightPx?: number;
};

type ImageDimensions = {
  width: number;
  height: number;
};

const EMPTY_OVERLAY: Record<number, OverlayPageState> = {};
const DEBUG_OVERLAY_LIMIT = 60;

const getFontFamily = (pdfFont: string) => {
  const lower = pdfFont.toLowerCase();
  if (lower.includes("times") || lower.includes("serif")) {
    return '"Times New Roman", Times, serif';
  }
  if (lower.includes("courier") || lower.includes("mono")) {
    return '"Courier New", Courier, monospace';
  }
  return "Helvetica, Arial, -apple-system, BlinkMacSystemFont, sans-serif";
};

const measureTextWidth = (text: string, fontSize: number, fontFamily: string): number => {
  if (typeof document === "undefined") {
    return text.length * fontSize * 0.6;
  }
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  if (!context) {
    return text.length * fontSize * 0.6;
  }
  context.font = `${fontSize}px ${fontFamily}`;
  return context.measureText(text).width;
};

export default function EditorPage() {
  const params = useParams<{ docId: string }>();
  const docId = params.docId;
  const [pageCount, setPageCount] = useState(0);
  const [filename, setFilename] = useState("Loading…");
  const [sizeBytes, setSizeBytes] = useState(0);
  const [activePage, setActivePage] = useState(1);
  const [manifest, setManifest] = useState<ForgeManifest | null>(null);
  const [overlayByPage, setOverlayByPage] = useState<Record<number, OverlayPageState>>(
    EMPTY_OVERLAY
  );
  const [selectedOverlay, setSelectedOverlay] = useState<SelectedOverlay | null>(null);
  const [plan, setPlan] = useState<ForgeOverlayPlanResponse | null>(null);
  const [prompt, setPrompt] = useState("");
  const [planError, setPlanError] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [isPlanning, setIsPlanning] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [maskMode, setMaskMode] = useState<ExportMaskMode>("AUTO_BG");
  const [showDebugOverlay, setShowDebugOverlay] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [meta, manifestPayload] = await Promise.all([getDocumentMeta(docId), getForgeManifest(docId)]);
        if (cancelled) {
          return;
        }
        setFilename(meta.filename);
        setSizeBytes(meta.size_bytes);
        setPageCount(manifestPayload.page_count);
        setManifest(manifestPayload);
        setActivePage(1);
        setSelectedOverlay(null);
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof Error && err.message
              ? err.message
              : "We could not load the document metadata or forge manifest.";
          setError(`Unable to open this document. ${message} Return to the dashboard and retry.`);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [docId]);

  useEffect(() => {
    let cancelled = false;
    async function loadOverlays() {
      if (!manifest) {
        return;
      }
      try {
        const overlays = await Promise.all(
          manifest.pages.map(async (page) => {
            const response = await getForgeOverlay(docId, page.page_index);
            return {
              pageIndex: page.page_index,
              overlay: response.overlay,
              masks: response.masks,
              pageImageWidthPx: response.page_image_width_px,
              pageImageHeightPx: response.page_image_height_px
            };
          })
        );
        if (cancelled) {
          return;
        }
        const nextOverlay: Record<number, OverlayPageState> = {};
        overlays.forEach(({ pageIndex, overlay, masks, pageImageWidthPx, pageImageHeightPx }) => {
          nextOverlay[pageIndex] = {
            entries: overlay.reduce<Record<string, ForgeOverlayEntry>>((acc, entry) => {
              acc[entry.element_id] = entry;
              return acc;
            }, {}),
            masks,
            pageImageWidthPx,
            pageImageHeightPx
          };
        });
        setOverlayByPage(nextOverlay);
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof Error && err.message ? err.message : "We could not load the overlay state.";
          setError(`Unable to open this document. ${message}`);
        }
      }
    }
    void loadOverlays();
    return () => {
      cancelled = true;
    };
  }, [docId, manifest]);

  const sizeLabel = useMemo(() => {
    if (!sizeBytes) {
      return "0 KB";
    }
    const kb = sizeBytes / 1024;
    if (kb < 1024) {
      return `${kb.toFixed(1)} KB`;
    }
    return `${(kb / 1024).toFixed(1)} MB`;
  }, [sizeBytes]);

  useEffect(() => {
    if (!activePage) {
      return;
    }
    const target = document.getElementById(`page-${activePage}`);
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [activePage]);

  if (error) {
    return <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-6">{error}</div>;
  }

  const handleExport = () => {
    window.open(exportPdfUrl(docId, maskMode), "_blank", "noopener,noreferrer");
  };

  const handleSelect = (pageIndex: number, item: ForgeManifestElement, overlayEntry?: ForgeOverlayEntry) => {
    setActivePage(pageIndex + 1);
    setSelectedOverlay({
      page_index: pageIndex,
      element_id: item.element_id,
      text: overlayEntry?.text ?? item.text,
      bbox: item.bbox,
      content_hash: overlayEntry?.content_hash ?? "",
      element_type: item.element_type,
      style: item.style
    });
    setPlan(null);
    setPlanError(null);
    setApplyError(null);
  };

  const selectionSnapshot: ForgeOverlaySelection[] | null = selectedOverlay
    ? [
        {
          element_id: selectedOverlay.element_id,
          text: selectedOverlay.text,
          content_hash: selectedOverlay.content_hash,
          bbox: selectedOverlay.bbox,
          element_type: selectedOverlay.element_type,
          style: selectedOverlay.style
        }
      ]
    : null;

  const handlePlan = async () => {
    if (!selectedOverlay || !selectionSnapshot) {
      setPlanError("Select a text element first.");
      return;
    }
    if (!prompt.trim()) {
      setPlanError("Enter a request for the selected element.");
      return;
    }
    setIsPlanning(true);
    setPlanError(null);
    try {
      const response = await planOverlayPatch({
        doc_id: docId,
        page_index: selectedOverlay.page_index,
        selection: selectionSnapshot,
        user_prompt: prompt.trim()
      });
      setPlan(response);
    } catch (err) {
      setPlanError(err instanceof Error ? err.message : "Unable to plan overlay change.");
    } finally {
      setIsPlanning(false);
    }
  };

  const handleApply = async () => {
    if (!selectedOverlay || !selectionSnapshot || !plan) {
      setApplyError("No overlay plan to apply.");
      return;
    }
    setIsApplying(true);
    setApplyError(null);
    try {
      const response = await commitOverlayPatch(docId, {
        doc_id: docId,
        page_index: selectedOverlay.page_index,
        selection: selectionSnapshot,
        ops: plan.ops
      });
      setOverlayByPage((prev) => ({
        ...prev,
        [selectedOverlay.page_index]: {
          entries: response.overlay.reduce<Record<string, ForgeOverlayEntry>>((acc, entry) => {
            acc[entry.element_id] = entry;
            return acc;
          }, {}),
          masks: response.masks,
          pageImageWidthPx: prev[selectedOverlay.page_index]?.pageImageWidthPx,
          pageImageHeightPx: prev[selectedOverlay.page_index]?.pageImageHeightPx
        }
      }));
      const updatedEntry = response.overlay.find((entry) => entry.element_id === selectedOverlay.element_id);
      if (updatedEntry) {
        setSelectedOverlay((current) =>
          current
            ? {
                ...current,
                text: updatedEntry.text,
                content_hash: updatedEntry.content_hash
              }
            : current
        );
      }
      setPlan(null);
      setPrompt("");
    } catch (err) {
      setApplyError(err instanceof Error ? err.message : "Unable to apply overlay change.");
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <div className="flex h-full flex-col gap-6">
      <div className="flex items-center gap-4 rounded-2xl border border-forge-border bg-forge-panel/70 px-6 py-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-forge-card/70">
          <FileText className="h-6 w-6 text-forge-accent-soft" />
        </div>
        <div>
          <p className="text-sm text-slate-400">{filename}</p>
          <p className="text-lg font-semibold text-white">
            {pageCount ? `${pageCount} pages` : "Loading pages"} · {sizeLabel}
          </p>
        </div>
      </div>

      <div className="grid flex-1 gap-6 lg:grid-cols-[220px_minmax(0,1fr)_320px]">
        <div className="hidden lg:block">
          {manifest ? (
            <div className="h-full overflow-y-auto rounded-2xl border border-forge-border bg-forge-panel/60 p-3">
              <div className="flex flex-col gap-4">
                {manifest.pages.map((page) => {
                  const pageNumber = page.page_index + 1;
                  const isActive = activePage === pageNumber;
                  return (
                    <button
                      key={`thumb_${pageNumber}`}
                      className={`rounded-xl border p-2 transition ${
                        isActive
                          ? "border-forge-accent bg-forge-card/80"
                          : "border-forge-border bg-forge-card/40 hover:border-forge-accent/70"
                      }`}
                      type="button"
                      onClick={() => setActivePage(pageNumber)}
                    >
                      <img
                        src={apiUrl(page.image_path)}
                        alt={`Page ${pageNumber}`}
                        className="h-auto w-full rounded-lg"
                      />
                      <div className="mt-2 text-center text-xs text-slate-400">Page {pageNumber}</div>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-forge-border bg-forge-panel/60 p-4 text-sm text-slate-400">
              Loading thumbnails…
            </div>
          )}
        </div>

        <div className="flex h-full flex-col gap-4">
          <div className="flex items-center justify-between gap-3 rounded-2xl border border-forge-border bg-forge-card/70 px-4 py-3">
            <div>
              <div className="text-sm text-slate-300">Overlay editor</div>
              <div className="text-xs text-slate-500">Click text to edit</div>
            </div>
            <button
              type="button"
              onClick={() => setShowDebugOverlay((prev) => !prev)}
              className={`rounded-full border px-3 py-1 text-xs ${
                showDebugOverlay
                  ? "border-forge-accent text-forge-accent"
                  : "border-forge-border text-slate-400"
              }`}
            >
              {showDebugOverlay ? "Debug on" : "Debug off"}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto scroll-smooth rounded-2xl border border-forge-border bg-forge-panel/50 p-4">
            {!manifest ? (
              <div className="text-sm text-slate-400">Loading document…</div>
            ) : (
              manifest.pages.map((page) => {
                const overlayState = overlayByPage[page.page_index];
                return (
                  <div
                    key={`page_${page.page_index}`}
                    id={`page-${page.page_index + 1}`}
                    className="mb-6 flex justify-center"
                  >
                    <OverlayPageCanvas
                      page={page}
                      overlayState={overlayState}
                      selectedOverlay={selectedOverlay}
                      showDebugOverlay={showDebugOverlay}
                      onSelect={handleSelect}
                    />
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-2xl border border-forge-border bg-forge-card/60 p-4">
            <h3 className="text-sm font-semibold text-slate-200">Inspector</h3>
            {selectedOverlay ? (
              <div className="mt-3 space-y-2 text-xs text-slate-300">
                <p>
                  <span className="text-slate-400">Element ID:</span> {selectedOverlay.element_id}
                </p>
                <p>
                  <span className="text-slate-400">Page:</span> {selectedOverlay.page_index + 1}
                </p>
                <p>
                  <span className="text-slate-400">Text:</span> {selectedOverlay.text}
                </p>
                <p>
                  <span className="text-slate-400">BBox:</span>{" "}
                  {selectedOverlay.bbox.map((value) => value.toFixed(2)).join(", ")}
                </p>
              </div>
            ) : (
              <p className="mt-3 text-xs text-slate-400">Select a text element to view details.</p>
            )}
          </div>

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
                placeholder="e.g., Change this to Panel B"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
              />
              <button
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-forge-border bg-forge-card/70 px-3 py-2 text-xs text-slate-200"
                type="button"
                onClick={() => void handlePlan()}
                disabled={isPlanning || !prompt.trim()}
              >
                <Send className="h-3.5 w-3.5" />
                {isPlanning ? "Planning…" : "Plan patch"}
              </button>
              {planError ? <p className="text-xs text-red-300">{planError}</p> : null}
            </div>

            {plan ? (
              <div className="mt-4 rounded-xl border border-forge-border bg-forge-panel/60 p-3 text-xs text-slate-300">
                <p className="text-[11px] text-slate-400">Proposed changes</p>
                <ul className="mt-2 space-y-1">
                  {plan.ops.map((op) => (
                    <li key={`${op.type}-${op.element_id}`}>
                      <span className="text-slate-400">{op.element_id.slice(0, 6)}:</span> {op.new_text}
                    </li>
                  ))}
                </ul>
                <div className="mt-3 flex gap-2">
                  <button
                    className="flex-1 rounded-lg border border-forge-border bg-forge-card/70 px-3 py-2 text-xs text-slate-200"
                    type="button"
                    onClick={() => void handleApply()}
                    disabled={isApplying}
                  >
                    {isApplying ? "Applying…" : "Apply"}
                  </button>
                  <button
                    className="flex-1 rounded-lg border border-forge-border bg-forge-panel/60 px-3 py-2 text-xs text-slate-300"
                    type="button"
                    onClick={() => setPlan(null)}
                  >
                    Cancel
                  </button>
                </div>
                {applyError ? <p className="mt-2 text-xs text-red-300">{applyError}</p> : null}
              </div>
            ) : null}
          </div>
          <div className="rounded-2xl border border-forge-border bg-forge-card/60 p-4">
            <h3 className="text-sm font-semibold text-slate-200">Export</h3>
            <div className="mt-3 space-y-3 text-xs text-slate-400">
              <label className="block text-xs uppercase tracking-wide text-slate-500">
                Mask mode
                <select
                  className="mt-2 w-full rounded-xl border border-forge-border bg-forge-panel/60 px-3 py-2 text-sm text-white"
                  value={maskMode}
                  onChange={(event) => setMaskMode(event.target.value as ExportMaskMode)}
                >
                  <option value="AUTO_BG">Auto background</option>
                  <option value="SOLID">Solid white</option>
                </select>
              </label>
              <button
                type="button"
                onClick={handleExport}
                className="w-full rounded-full bg-forge-accent px-4 py-2 text-sm font-semibold text-white shadow-glow"
              >
                Export PDF
              </button>
            </div>
          </div>
          <div className="rounded-2xl border border-forge-border bg-forge-card/60 p-4">
            <h3 className="text-sm font-semibold text-slate-200">Document</h3>
            <div className="mt-3 space-y-2 text-xs text-slate-400">
              <p>Filename: {filename}</p>
              <p>Pages: {pageCount || "…"}</p>
              <p>Size: {sizeLabel}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

type ForgeManifestPage = ForgeManifest["pages"][number];

function OverlayPageCanvas({
  page,
  overlayState,
  selectedOverlay,
  showDebugOverlay,
  onSelect
}: {
  page: ForgeManifestPage;
  overlayState?: OverlayPageState;
  selectedOverlay: SelectedOverlay | null;
  showDebugOverlay: boolean;
  onSelect: (pageIndex: number, item: ForgeManifestElement, overlayEntry?: ForgeOverlayEntry) => void;
}) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [containerSize, setContainerSize] = useState<ImageDimensions>({ width: 0, height: 0 });
  const [imageLoaded, setImageLoaded] = useState(false);
  const overlayBboxes = useMemo<BBox[]>(() => {
    const maskBboxes = overlayState?.masks?.map((mask) => mask.bbox as BBox) ?? [];
    const elementBboxes = page.elements.map((element) => element.bbox as BBox);
    return [...maskBboxes, ...elementBboxes];
  }, [overlayState?.masks, page.elements]);

  const { toPixelRect } = useMemo(
    () =>
      createBBoxConverter(overlayBboxes, {
        containerWidth: containerSize.width,
        containerHeight: containerSize.height,
        pageWidthPt: page.width_pt,
        pageHeightPt: page.height_pt,
        imageWidthPx: overlayState?.pageImageWidthPx,
        imageHeightPx: overlayState?.pageImageHeightPx
      }),
    [
      overlayBboxes,
      containerSize.height,
      containerSize.width,
      page.height_pt,
      page.width_pt,
      overlayState?.pageImageHeightPx,
      overlayState?.pageImageWidthPx
    ]
  );

  useEffect(() => {
    const img = imgRef.current;
    if (!img) {
      return;
    }

    const updateSize = () => {
      setContainerSize({
        width: img.clientWidth,
        height: img.clientHeight
      });
    };

    const observer = new ResizeObserver(updateSize);
    observer.observe(img);
    img.addEventListener("load", updateSize);

    return () => {
      observer.disconnect();
      img.removeEventListener("load", updateSize);
    };
  }, []);

  return (
    <div className="relative inline-block max-w-full shadow-xl" data-page-index={page.page_index}>
      <img
        ref={imgRef}
        src={apiUrl(page.image_path)}
        alt={`Page ${page.page_index + 1}`}
        className="block h-auto max-w-full"
        onLoad={() => setImageLoaded(true)}
      />

      {imageLoaded && containerSize.width > 0 ? (
        <div className="absolute inset-0 pointer-events-none">
          {overlayState?.masks?.map((mask, idx) => {
            const rect = toPixelRect(mask.bbox as BBox);

            return (
              <div
                key={`mask_${idx}`}
                style={{
                  position: "absolute",
                  left: rect.left,
                  top: rect.top,
                  width: rect.width,
                  height: rect.height,
                  backgroundColor: mask.color
                }}
              />
            );
          })}

          {page.elements.map((element) => {
            const overlayEntry = overlayState?.entries?.[element.element_id];
            const displayText = overlayEntry?.text ?? element.text;
            const isSelected = selectedOverlay?.element_id === element.element_id;
            const isEdited = Boolean(overlayEntry);

            const rect = toPixelRect(element.bbox as BBox);

            const fontFamily = getFontFamily(element.style.font_family || "");
            let fontSize = (element.style.font_size_pt / page.width_pt) * containerSize.width;
            const textWidth = measureTextWidth(displayText, fontSize, fontFamily);
            if (textWidth > rect.width * 1.1) {
              const scaleFactor = rect.width / textWidth;
              fontSize = fontSize * scaleFactor * 0.95;
            }

            return (
              <div
                key={element.element_id}
                onClick={() => onSelect(page.page_index, element, overlayEntry)}
                className={`absolute cursor-pointer pointer-events-auto transition-all duration-150 ${
                  isSelected
                    ? "ring-2 ring-blue-500 bg-blue-500/10 z-20"
                    : "hover:ring-1 hover:ring-blue-300/50 hover:bg-blue-300/5"
                }`}
                style={{
                  left: rect.left,
                  top: rect.top,
                  width: rect.width,
                  height: rect.height,
                  color: isEdited ? (element.style.color || "#000") : "transparent",
                  backgroundColor: isEdited ? "#fff" : undefined,
                  fontSize,
                  fontWeight: element.style.is_bold ? "bold" : "normal",
                  fontFamily,
                  lineHeight: element.element_type === "text" ? 1.4 : 1.2,
                  whiteSpace: element.element_type === "text" ? "pre-wrap" : "pre-wrap",
                  overflow: "visible",
                  padding: "0px",
                  display: "flex",
                  alignItems: "flex-start"
                }}
              >
                {displayText}
              </div>
            );
          })}

          {showDebugOverlay
            ? page.elements.slice(0, DEBUG_OVERLAY_LIMIT).map((element) => {
                const rect = toPixelRect(element.bbox as BBox);

                return (
                  <div
                    key={`debug_${element.element_id}`}
                    style={{
                      position: "absolute",
                      left: rect.left,
                      top: rect.top,
                      width: rect.width,
                      height: rect.height,
                      border: "1px solid yellow",
                      pointerEvents: "none"
                    }}
                  >
                    <span className="text-xs bg-yellow-500/50 px-1">
                      {element.element_id}
                    </span>
                  </div>
                );
              })
            : null}
        </div>
      ) : null}
    </div>
  );
}
