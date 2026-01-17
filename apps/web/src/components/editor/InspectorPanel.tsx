import { FileText, Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { DecodeResponse, DocumentMeta } from "@/lib/api";

interface InspectorPanelProps {
  meta: DocumentMeta | null;
  decode: DecodeResponse | null;
}

export function InspectorPanel({ meta, decode }: InspectorPanelProps) {
  return (
    <Card className="flex h-full flex-col gap-6 p-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-ink-700">
          <FileText className="h-5 w-5 text-frost-100" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-frost-200/60">Inspector</p>
          <p className="text-base font-semibold">Document metadata</p>
        </div>
      </div>

      <div className="space-y-3 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-frost-200/70">Filename</span>
          <span className="max-w-[140px] truncate text-right">{meta?.filename ?? "Loading"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-frost-200/70">Size</span>
          <span>{meta ? `${(meta.size_bytes / 1024).toFixed(1)} KB` : "-"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-frost-200/70">Pages</span>
          <span>{decode?.page_count ?? "-"}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-frost-200/70">Rotation</span>
          <span>{decode?.pages?.[0]?.rotation ?? "-"}</span>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-frost-200/60">
          <Info className="h-4 w-4" />
          decode status
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge>{decode ? "Decoded" : "Loading"}</Badge>
          <Badge>Deterministic</Badge>
        </div>
      </div>
    </Card>
  );
}
