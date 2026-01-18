"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { FileText } from "lucide-react";

import { ChatDock } from "@/components/editor/ChatDock";
import { InspectorPanel } from "@/components/editor/InspectorPanel";
import { PatchTimeline } from "@/components/editor/PatchTimeline";
import { PdfStage, PdfThumbnails } from "@/components/editor/PdfStage";
import { exportPdfUrl, getDecode, getDocumentMeta, type ExportMaskMode } from "@/lib/api";

export default function EditorPage() {
  const params = useParams<{ docId: string }>();
  const docId = params.docId;
  const [pageCount, setPageCount] = useState(0);
  const [filename, setFilename] = useState("Loading…");
  const [sizeBytes, setSizeBytes] = useState(0);
  const [activePage, setActivePage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [maskMode, setMaskMode] = useState<ExportMaskMode>("AUTO_BG");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [meta, decode] = await Promise.all([getDocumentMeta(docId), getDecode(docId)]);
        if (cancelled) {
          return;
        }
        setFilename(meta.filename);
        setSizeBytes(meta.size_bytes);
        setPageCount(decode.page_count);
        setActivePage(1);
      } catch (err) {
        if (!cancelled) {
          setError("Unable to load document. Please return to dashboard and retry.");
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [docId]);

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
          {pageCount > 0 ? (
            <PdfThumbnails
              docId={docId}
              pageCount={pageCount}
              activePage={activePage}
              onSelect={setActivePage}
            />
          ) : (
            <div className="rounded-2xl border border-forge-border bg-forge-panel/60 p-4 text-sm text-slate-400">
              Loading thumbnails…
            </div>
          )}
        </div>

        <PdfStage docId={docId} initialPageCount={pageCount} />

        <div className="flex flex-col gap-4">
          <InspectorPanel docId={docId} />
          <PatchTimeline docId={docId} pageIndex={activePage - 1} />
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
          <ChatDock docId={docId} />
        </div>
      </div>
    </div>
  );
}
