"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Minus, Plus, RefreshCw } from "lucide-react";

import { downloadUrl } from "@/lib/api";
import type { IRPage } from "@/lib/api";
import { useSelectionStore } from "@/lib/state/store";
import { SelectionLayer } from "@/components/editor/SelectionLayer";

type ReactPdfModule = typeof import("react-pdf");

function useReactPdf() {
  const [module, setModule] = useState<ReactPdfModule | null>(null);

  useEffect(() => {
    let mounted = true;
    import("react-pdf").then((mod) => {
      if (!mounted) {
        return;
      }
      if (typeof window !== "undefined") {
        mod.pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
      }
      setModule(mod);
    });
    return () => {
      mounted = false;
    };
  }, []);

  return module;
}

interface PdfStageProps {
  docId: string;
  initialPageCount?: number;
}

export function PdfStage({ docId, initialPageCount }: PdfStageProps) {
  const [scale, setScale] = useState(1);
  const [numPages, setNumPages] = useState<number | null>(initialPageCount ?? null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const fileUrl = useMemo(() => downloadUrl(docId), [docId]);
  const cycleCandidate = useSelectionStore((state) => state.cycleCandidate);
  const loadPatchsets = useSelectionStore((state) => state.loadPatchsets);
  const reactPdf = useReactPdf();

  useEffect(() => {
    void loadPatchsets(docId);
  }, [docId, loadPatchsets]);

  useEffect(() => {
    setPdfError(null);
  }, [docId, fileUrl]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Tab") {
        event.preventDefault();
        cycleCandidate();
      }
    };
    window.addEventListener("keydown", handler);
    return () => {
      window.removeEventListener("keydown", handler);
    };
  }, [cycleCandidate]);

  if (!reactPdf) {
    return (
      <div className="flex h-full items-center justify-center rounded-2xl border border-forge-border bg-forge-panel/60 text-sm text-slate-400">
        Loading PDF viewer…
      </div>
    );
  }

  const { Document, Page } = reactPdf;

  async function handlePdfLoadError(error: unknown) {
    console.error("PDF failed to load", error);
    try {
      const response = await fetch(fileUrl, {
        headers: {
          Range: "bytes=0-1"
        }
      });
      if (!response.ok) {
        const bodyText = await response.text();
        const snippet = bodyText.trim().slice(0, 180);
        setPdfError(
          `PDF download failed (${response.status}).${snippet ? ` ${snippet}` : ""}`
        );
        return;
      }
      setPdfError(
        `PDF download failed (${response.status}). ${
          error instanceof Error && error.message ? error.message : "Unknown error"
        }`
      );
    } catch (fetchError) {
      setPdfError(
        `PDF download failed. ${
          fetchError instanceof Error && fetchError.message ? fetchError.message : "Unknown error"
        }`
      );
    }
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center justify-between rounded-2xl border border-forge-border bg-forge-card/70 px-4 py-3">
        <div className="text-sm text-slate-300">Zoom</div>
        <div className="flex items-center gap-2">
          <button
            className="rounded-lg border border-forge-border bg-forge-panel/70 p-2 text-slate-200"
            onClick={() => setScale((prev) => Math.max(0.6, Number((prev - 0.1).toFixed(2))))}
            type="button"
          >
            <Minus className="h-4 w-4" />
          </button>
          <span className="min-w-[60px] text-center text-sm text-slate-200">
            {Math.round(scale * 100)}%
          </span>
          <button
            className="rounded-lg border border-forge-border bg-forge-panel/70 p-2 text-slate-200"
            onClick={() => setScale((prev) => Math.min(2, Number((prev + 0.1).toFixed(2))))}
            type="button"
          >
            <Plus className="h-4 w-4" />
          </button>
          <button
            className="rounded-lg border border-forge-border bg-forge-panel/70 p-2 text-slate-200"
            onClick={() => setScale(1)}
            type="button"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scroll-smooth rounded-2xl border border-forge-border bg-forge-panel/50 p-4">
        {pdfError ? (
          <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
            {pdfError}
          </div>
        ) : null}
        <Document
          file={fileUrl}
          onLoadSuccess={(pdf) => setNumPages(pdf.numPages)}
          onLoadError={handlePdfLoadError}
          loading={<div className="text-sm text-slate-400">Loading document…</div>}
        >
          {Array.from({ length: numPages ?? 0 }, (_, index) => (
            <div
              key={`page_${index + 1}`}
              id={`page-${index + 1}`}
              className="mb-6 flex justify-center"
            >
              <PageWithOverlay docId={docId} pageIndex={index} scale={scale} PageComponent={Page} />
            </div>
          ))}
        </Document>
      </div>
    </div>
  );
}

interface PdfThumbnailsProps {
  docId: string;
  pageCount: number;
  activePage?: number;
  onSelect?: (page: number) => void;
}

export function PdfThumbnails({ docId, pageCount, activePage, onSelect }: PdfThumbnailsProps) {
  const fileUrl = useMemo(() => downloadUrl(docId), [docId]);
  const reactPdf = useReactPdf();
  const [pdfError, setPdfError] = useState<string | null>(null);

  useEffect(() => {
    setPdfError(null);
  }, [docId, fileUrl]);

  if (!reactPdf) {
    return (
      <div className="h-full rounded-2xl border border-forge-border bg-forge-panel/60 p-3 text-xs text-slate-500">
        Loading thumbnails…
      </div>
    );
  }

  const { Document, Page } = reactPdf;

  return (
    <div className="h-full overflow-y-auto rounded-2xl border border-forge-border bg-forge-panel/60 p-3">
      {pdfError ? (
        <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-200">
          {pdfError}
        </div>
      ) : null}
      <Document
        file={fileUrl}
        loading={<div className="text-xs text-slate-500">Loading…</div>}
        onLoadError={(error) => {
          console.error("PDF thumbnails failed to load", error);
          setPdfError(
            `Thumbnails unavailable. ${
              error instanceof Error && error.message ? error.message : "Unknown error"
            }`
          );
        }}
      >
        <div className="flex flex-col gap-4">
          {Array.from({ length: pageCount }, (_, index) => {
            const pageNumber = index + 1;
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
                onClick={() => onSelect?.(pageNumber)}
              >
                <Page
                  pageNumber={pageNumber}
                  width={150}
                  renderAnnotationLayer={false}
                  renderTextLayer={false}
                />
                <div className="mt-2 text-center text-xs text-slate-400">Page {pageNumber}</div>
              </button>
            );
          })}
        </div>
      </Document>
    </div>
  );
}

interface PageWithOverlayProps {
  docId: string;
  pageIndex: number;
  scale: number;
  PageComponent: ReactPdfModule["Page"];
}

function PageWithOverlay({ docId, pageIndex, scale, PageComponent }: PageWithOverlayProps) {
  const [pageIR, setPageIR] = useState<IRPage | null>(null);
  const [renderedSize, setRenderedSize] = useState({ width: 0, height: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const previewComposite = useSelectionStore((state) => state.previewComposite);
  const patchsets = useSelectionStore((state) => state.patchsets);
  const patchVisibility = useSelectionStore((state) => state.patchVisibility);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        await previewComposite(docId, pageIndex);
        if (cancelled) {
          return;
        }
        const compositePage = useSelectionStore.getState().irPages[pageIndex] ?? null;
        setPageIR(compositePage);
      } catch (error) {
        console.error("Failed to load IR page", error);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [docId, pageIndex, previewComposite, patchsets, patchVisibility]);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return;
    }
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setRenderedSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height
        });
      }
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={containerRef} className="relative inline-block">
      <PageComponent
        pageNumber={pageIndex + 1}
        scale={scale}
        renderAnnotationLayer={false}
        renderTextLayer={false}
      />
      {pageIR && renderedSize.width > 0 && renderedSize.height > 0 ? (
        <SelectionLayer
          docId={docId}
          pageIndex={pageIndex}
          page={pageIR}
          renderedWidth={renderedSize.width}
          renderedHeight={renderedSize.height}
        />
      ) : null}
    </div>
  );
}
