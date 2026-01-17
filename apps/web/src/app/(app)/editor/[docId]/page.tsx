"use client";

import { useEffect, useState } from "react";

import { ChatDock } from "@/components/editor/ChatDock";
import { InspectorPanel } from "@/components/editor/InspectorPanel";
import { Minimap } from "@/components/editor/Minimap";
import { PdfStage } from "@/components/editor/PdfStage";
import type { DecodeResponse, DocumentMeta } from "@/lib/api";
import { getDecode, getDocumentMeta, getDownloadUrl } from "@/lib/api";

interface EditorPageProps {
  params: { docId: string };
}

export default function EditorPage({ params }: EditorPageProps) {
  const [meta, setMeta] = useState<DocumentMeta | null>(null);
  const [decode, setDecode] = useState<DecodeResponse | null>(null);
  const [pageCount, setPageCount] = useState(1);

  useEffect(() => {
    const fetchData = async () => {
      const [metaData, decodeData] = await Promise.all([
        getDocumentMeta(params.docId),
        getDecode(params.docId),
      ]);
      setMeta(metaData);
      setDecode(decodeData);
      setPageCount(decodeData.page_count || 1);
    };

    fetchData().catch(() => null);
  }, [params.docId]);

  const fileUrl = getDownloadUrl(params.docId);

  return (
    <div className="grid h-[calc(100vh-160px)] grid-cols-[220px_1fr_320px] gap-6">
      <Minimap fileUrl={fileUrl} pageCount={pageCount} onPageCount={setPageCount} />
      <div className="flex flex-col gap-4">
        <PdfStage fileUrl={fileUrl} pageCount={pageCount} onPageCount={setPageCount} />
        <ChatDock />
      </div>
      <InspectorPanel meta={meta} decode={decode} />
    </div>
  );
}
