"use client";

import { useMemo, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { Minus, Plus, RefreshCw } from "lucide-react";

import { downloadUrl } from "@/lib/api";

if (typeof window !== "undefined") {
  pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
}

interface PdfStageProps {
  docId: string;
  initialPageCount?: number;
}

export function PdfStage({ docId, initialPageCount }: PdfStageProps) {
  const [scale, setScale] = useState(1);
  const [numPages, setNumPages] = useState<number | null>(initialPageCount ?? null);
  const fileUrl = useMemo(() => downloadUrl(docId), [docId]);

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
        <Document
          file={fileUrl}
          onLoadSuccess={(pdf) => setNumPages(pdf.numPages)}
          loading={<div className="text-sm text-slate-400">Loading document…</div>}
        >
          {Array.from({ length: numPages ?? 0 }, (_, index) => (
            <div
              key={`page_${index + 1}`}
              id={`page-${index + 1}`}
              className="mb-6 flex justify-center"
            >
              <Page
                pageNumber={index + 1}
                scale={scale}
                renderAnnotationLayer={false}
                renderTextLayer={false}
              />
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

  return (
    <div className="h-full overflow-y-auto rounded-2xl border border-forge-border bg-forge-panel/60 p-3">
      <Document file={fileUrl} loading={<div className="text-xs text-slate-500">Loading…</div>}>
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
