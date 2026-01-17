"use client";

import "@/lib/pdf/pdfjs";

import { useEffect, useMemo, useRef } from "react";
import { Document, Page } from "react-pdf";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useEditorStore } from "@/lib/state/store";

interface PdfStageProps {
  fileUrl: string;
  pageCount: number;
  onPageCount: (count: number) => void;
}

export function PdfStage({ fileUrl, pageCount, onPageCount }: PdfStageProps) {
  const zoom = useEditorStore((state) => state.zoom);
  const setZoom = useEditorStore((state) => state.setZoom);
  const selectedPage = useEditorStore((state) => state.selectedPage);
  const setSelectedPage = useEditorStore((state) => state.setSelectedPage);
  const pageRefs = useRef<Array<HTMLDivElement | null>>([]);

  const pages = useMemo(() => {
    return Array.from({ length: pageCount }, (_, i) => i + 1);
  }, [pageCount]);

  useEffect(() => {
    const pageRef = pageRefs.current[selectedPage - 1];
    if (pageRef) {
      pageRef.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [selectedPage]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between rounded-2xl border border-ink-700 bg-ink-900/70 px-4 py-3">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setZoom(Math.max(0.5, zoom - 0.1))}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="text-sm text-frost-200/70">{Math.round(zoom * 100)}%</span>
          <Button variant="ghost" size="sm" onClick={() => setZoom(Math.min(2.5, zoom + 0.1))}>
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedPage(Math.max(1, selectedPage - 1))}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span>
            Page {selectedPage} / {pageCount || 1}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedPage(Math.min(pageCount || 1, selectedPage + 1))}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="mt-4 flex-1 overflow-y-auto rounded-2xl border border-ink-700 bg-ink-900/40 px-4 py-6">
        <Document
          file={fileUrl}
          onLoadSuccess={(doc) => {
            onPageCount(doc.numPages);
          }}
          loading={<p className="text-sm text-frost-200/70">Loading PDF...</p>}
        >
          <div className="space-y-6">
            {pages.map((page) => (
              <div
                key={page}
                ref={(el) => {
                  pageRefs.current[page - 1] = el;
                }}
                className="flex justify-center"
              >
                <Page
                  pageNumber={page}
                  scale={zoom}
                  renderTextLayer={true}
                  renderAnnotationLayer={false}
                />
              </div>
            ))}
          </div>
        </Document>
      </div>
    </div>
  );
}
