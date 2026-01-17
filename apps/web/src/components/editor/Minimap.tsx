"use client";

import "@/lib/pdf/pdfjs";

import { Document, Page } from "react-pdf";

import { useEditorStore } from "@/lib/state/store";
import { cn } from "@/lib/utils";

interface MinimapProps {
  fileUrl: string;
  pageCount: number;
  onPageCount: (count: number) => void;
}

export function Minimap({ fileUrl, pageCount, onPageCount }: MinimapProps) {
  const selectedPage = useEditorStore((state) => state.selectedPage);
  const setSelectedPage = useEditorStore((state) => state.setSelectedPage);

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto rounded-3xl border border-ink-700 bg-ink-900/70 p-4">
      <p className="text-xs uppercase tracking-[0.3em] text-frost-200/60">Pages</p>
      <Document
        file={fileUrl}
        onLoadSuccess={(doc) => onPageCount(doc.numPages)}
        loading={<p className="text-xs text-frost-200/70">Loading...</p>}
      >
        <div className="space-y-3">
          {Array.from({ length: pageCount }, (_, i) => i + 1).map((page) => (
            <button
              key={page}
              type="button"
              onClick={() => setSelectedPage(page)}
              className={cn(
                "w-full rounded-2xl border border-transparent p-2 transition",
                selectedPage === page
                  ? "border-accent-400 bg-ink-800/80"
                  : "hover:border-ink-700"
              )}
            >
              <Page pageNumber={page} width={140} renderTextLayer={false} renderAnnotationLayer={false} />
              <p className="mt-2 text-center text-xs text-frost-200/70">Page {page}</p>
            </button>
          ))}
        </div>
      </Document>
    </div>
  );
}
