"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { FileText, MessageSquareText, Send } from "lucide-react";
import { GlobalWorkerOptions, getDocument } from "pdfjs-dist";
import type { PDFDocumentLoadingTask, PDFDocumentProxy } from "pdfjs-dist/types/src/display/api";

import {
  apiUrl,
  commitOverlayPatch,
  exportPdfUrl,
  getDecodedDocument,
  getDocumentFile,
  getDocumentMeta,
  getForgeManifest,
  getForgeOverlay,
  planOverlayPatch,
  type DecodedDocumentV1,
  type DecodedElementV1,
  type ExportMaskMode,
  type ForgeManifest,
  type ForgeManifestElement,
  type ForgeOverlayEntry,
  type ForgeOverlayMask,
  type ForgeOverlayPlanResponse,
  type ForgeOverlaySelection
} from "@/lib/api";
import { PdfJsPage } from "@/components/editor/PdfJsPage";
import { commitOverlayWithRetry } from "@/lib/overlay-commit";
import { getPdfWorkerSrc } from "@/lib/pdfjs";
import { area, pickDecodedElementsInRegion, type BBox } from "@/components/editor/decodedHitTest";

type DecodedSelection = {
  page_index: number;
  region_bbox_norm: BBox;
  elements: DecodedElementV1[];
  primary_id: string | null;
};

const toDecodedStyle = (element: DecodedElementV1) =>
  element.style ?? {
    font_name: element.font_name ?? null,
    font_size_pt: element.font_size_pt ?? null,
    color: element.color ?? null
  };

const toOverlayStyle = (element: DecodedElementV1): ForgeManifestElement["style"] => ({
  font_size_pt: element.font_size_pt ?? 12,
  is_bold: false,
  is_italic: false,
  color: element.color ?? "#000",
  font_family: element.font_name ?? "Helvetica"
});

type OverlayPageState = {
  entries: Record<string, ForgeOverlayEntry>;
  masks: ForgeOverlayMask[];
  pageImageWidthPx?: number;
  pageImageHeightPx?: number;
};

const EMPTY_OVERLAY: Record<number, OverlayPageState> = {};

export default function EditorPage() {
  const params = useParams<{ docId: string }>();
  const docId = params.docId;
  const [pageCount, setPageCount] = useState(0);
  const [filename, setFilename] = useState("Loading…");
  const [sizeBytes, setSizeBytes] = useState(0);
  const [activePage, setActivePage] = useState(1);
  const [manifest, setManifest] = useState<ForgeManifest | null>(null);
  const [decodedDoc, setDecodedDoc] = useState<DecodedDocumentV1 | null>(null);
  const [decodedError, setDecodedError] = useState<string | null>(null);
  const [overlayByPage, setOverlayByPage] = useState<Record<number, OverlayPageState>>(
    EMPTY_OVERLAY
  );
  const [pdfDocument, setPdfDocument] = useState<PDFDocumentProxy | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const pdfDocRef = useRef<PDFDocumentProxy | null>(null);
  const [decodedSelection, setDecodedSelection] = useState<DecodedSelection | null>(null);
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
    if (typeof window !== "undefined") {
      GlobalWorkerOptions.workerSrc = getPdfWorkerSrc();
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    let loadingTask: PDFDocumentLoadingTask | null = null;

    async function loadPdf() {
      setPdfDocument(null);
      setPdfError(null);
      try {
        if (pdfDocRef.current) {
          await pdfDocRef.current.destroy();
          pdfDocRef.current = null;
        }
        const data = await getDocumentFile(docId);
        if (cancelled) {
          return;
        }
        loadingTask = getDocument({ data });
        const doc = await loadingTask.promise;
        if (cancelled) {
          await doc.destroy();
          return;
        }
        pdfDocRef.current = doc;
        setPdfDocument(doc);
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof Error && err.message
              ? err.message
              : "We could not load the PDF file.";
          setPdfError(message);
        }
      }
    }

    void loadPdf();
    return () => {
      cancelled = true;
      void loadingTask?.destroy();
      void pdfDocRef.current?.destroy();
      pdfDocRef.current = null;
    };
  }, [docId]);

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
        setDecodedSelection(null);
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
    async function loadDecoded() {
      setDecodedDoc(null);
      setDecodedError(null);
      try {
        const decoded = await getDecodedDocument(docId);
        if (!cancelled) {
          setDecodedDoc(decoded);
        }
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof Error && err.message
              ? err.message
              : "We could not load the decoded document data.";
          setDecodedError(message);
        }
      }
    }
    void loadDecoded();
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

  const refreshOverlayPage = async (pageIndex: number) => {
    const response = await getForgeOverlay(docId, pageIndex);
    const nextEntries = response.overlay.reduce<Record<string, ForgeOverlayEntry>>((acc, entry) => {
      acc[entry.element_id] = entry;
      return acc;
    }, {});
    setOverlayByPage((prev) => ({
      ...prev,
      [pageIndex]: {
        entries: nextEntries,
        masks: response.masks,
        pageImageWidthPx: response.page_image_width_px,
        pageImageHeightPx: response.page_image_height_px
      }
    }));
    return response;
  };

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

  const handleRegionSelect = (pageIndex: number, bboxNorm: BBox) => {
    setActivePage(pageIndex + 1);
    if (!decodedDoc) {
      setPlanError("Decoded document data is still loading.");
      return;
    }
    const decodedPage = decodedDoc.pages.find((page) => page.page_index === pageIndex);
    if (!decodedPage) {
      setPlanError("Decoded page data not found.");
      return;
    }
    const selected = pickDecodedElementsInRegion(decodedPage.elements, bboxNorm);
    if (!selected.length) {
      setPlanError("No decoded text found in the selection.");
      return;
    }
    const primary = selected.reduce<{ id: string; size: number } | null>((best, element) => {
      const elementArea = area(element.bbox_norm);
      if (!best || elementArea < best.size) {
        return { id: element.id, size: elementArea };
      }
      return best;
    }, null);
    const nextSelection: DecodedSelection = {
      page_index: pageIndex,
      region_bbox_norm: bboxNorm,
      elements: selected,
      primary_id: primary?.id ?? null
    };
    setDecodedSelection(nextSelection);
    setPlan(null);
    setPlanError(null);
    setApplyError(null);
  };

  const selectionSnapshot: ForgeOverlaySelection[] | null = decodedSelection
    ? decodedSelection.elements.slice(0, 20).map((element) => ({
        element_id: element.id,
        text: element.text ?? "",
        content_hash: element.content_hash ?? "",
        bbox: element.bbox_norm,
        element_type: "text",
        style: toOverlayStyle(element)
      }))
    : null;

  const decodedSelectionPayload = decodedSelection
    ? {
        page_index: decodedSelection.page_index,
        region_bbox_norm: decodedSelection.region_bbox_norm,
        primary_id: decodedSelection.primary_id,
        elements: decodedSelection.elements.slice(0, 20).map((element) => ({
          id: element.id,
          kind: element.kind,
          bbox_norm: element.bbox_norm,
          text: element.text ?? undefined,
          font_name: element.font_name ?? undefined,
          font_size_pt: element.font_size_pt ?? undefined,
          color: element.color ?? undefined,
          style: toDecodedStyle(element),
          content_hash: element.content_hash ?? undefined
        }))
      }
    : undefined;

  const handlePlan = async () => {
    if (!decodedSelection || !selectionSnapshot) {
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
        page_index: decodedSelection.page_index,
        selection: selectionSnapshot,
        user_prompt: prompt.trim(),
        decoded_selection: decodedSelectionPayload
      });
      setPlan(response);
    } catch (err) {
      setPlanError(err instanceof Error ? err.message : "Unable to plan overlay change.");
    } finally {
      setIsPlanning(false);
    }
  };

  const handleApply = async () => {
    if (!decodedSelection || !selectionSnapshot || !plan) {
      setApplyError("No overlay plan to apply.");
      return;
    }
    setIsApplying(true);
    setApplyError(null);
    try {
      const { response, selection } = await commitOverlayWithRetry({
        docId,
        pageIndex: decodedSelection.page_index,
        selection: selectionSnapshot,
        ops: plan.ops,
        commitOverlayPatch,
        fetchOverlay: async (_docId, pageIndex) => refreshOverlayPage(pageIndex),
        decodedSelection: decodedSelectionPayload,
        fetchDecoded: async (_docId) => getDecodedDocument(_docId)
      });
      setOverlayByPage((prev) => ({
        ...prev,
        [decodedSelection.page_index]: {
          entries: response.overlay.reduce<Record<string, ForgeOverlayEntry>>((acc, entry) => {
            acc[entry.element_id] = entry;
            return acc;
          }, {}),
          masks: response.masks,
          pageImageWidthPx: prev[decodedSelection.page_index]?.pageImageWidthPx,
          pageImageHeightPx: prev[decodedSelection.page_index]?.pageImageHeightPx
        }
      }));
      const committedSelection = selection[0];
      const updatedEntry = committedSelection
        ? response.overlay.find((entry) => entry.element_id === committedSelection.element_id)
        : undefined;
      if (decodedSelection && committedSelection && updatedEntry) {
        setDecodedSelection((current) =>
          current
            ? {
                ...current,
                primary_id: committedSelection.element_id,
                elements: current.elements.map((element) =>
                  element.id === committedSelection.element_id
                    ? { ...element, text: updatedEntry.text, content_hash: updatedEntry.content_hash }
                    : element
                )
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
                      {/* eslint-disable-next-line @next/next/no-img-element */}
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
              <div className="text-xs text-slate-500">Drag to select text</div>
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
            ) : pdfError ? (
              <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
                {pdfError}
              </div>
            ) : decodedError ? (
              <div className="rounded-xl border border-yellow-500/40 bg-yellow-500/10 p-4 text-sm text-yellow-200">
                {decodedError}
              </div>
            ) : !pdfDocument ? (
              <div className="text-sm text-slate-400">Loading PDF…</div>
            ) : (
              manifest.pages.map((page) => {
                const overlayState = overlayByPage[page.page_index];
                return (
                  <div
                    key={`page_${page.page_index}`}
                    id={`page-${page.page_index + 1}`}
                    className="mb-6 flex justify-center"
                  >
                    <PdfJsPage
                      pdfDocument={pdfDocument}
                      pageIndex={page.page_index}
                      overlayEntries={overlayState?.entries}
                      overlayMasks={overlayState?.masks}
                      decodedPage={decodedDoc?.pages.find((item) => item.page_index === page.page_index) ?? null}
                      selectedDecodedIds={
                        decodedSelection?.page_index === page.page_index
                          ? decodedSelection.elements.map((element) => element.id)
                          : []
                      }
                      showDebugOverlay={showDebugOverlay}
                      onRegionSelect={handleRegionSelect}
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
            {decodedSelection ? (
              <div className="mt-3 space-y-2 text-xs text-slate-300">
                <p>
                  <span className="text-slate-400">Element ID:</span>{" "}
                  {decodedSelection.primary_id ?? "—"}
                </p>
                <p>
                  <span className="text-slate-400">Page:</span> {decodedSelection.page_index + 1}
                </p>
                <p>
                  <span className="text-slate-400">Text:</span>{" "}
                  {decodedSelection.elements.find((element) => element.id === decodedSelection.primary_id)?.text ??
                    "—"}
                </p>
                <p>
                  <span className="text-slate-400">BBox:</span>{" "}
                  {decodedSelection.region_bbox_norm.map((value) => value.toFixed(2)).join(", ")}
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
