"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { UploadCloud } from "lucide-react";

import { uploadDocument } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const handleFiles = useCallback(
    async (fileList: FileList | null) => {
      const file = fileList?.[0];
      if (!file) {
        return;
      }
      if (file.type !== "application/pdf") {
        setStatus("Please upload a PDF file.");
        return;
      }
      setStatus("Uploading…");
      try {
        const meta = await uploadDocument(file);
        router.push(`/editor/${meta.doc_id}`);
      } catch (error) {
        setStatus("Upload failed. Please try again.");
      }
    },
    [router]
  );

  return (
    <div className="flex h-full flex-col gap-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Dashboard</p>
        <h2 className="mt-2 text-2xl font-semibold text-white">Upload a PDF to begin</h2>
        <p className="mt-2 text-sm text-slate-400">
          Drag and drop a PDF or browse your files. We will route you directly into the editor.
        </p>
      </div>

      <div
        className={`flex min-h-[320px] flex-1 flex-col items-center justify-center rounded-3xl border border-dashed p-8 text-center transition ${
          isDragging
            ? "border-forge-accent bg-forge-card/80"
            : "border-forge-border bg-forge-panel/60"
        }`}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          handleFiles(event.dataTransfer.files);
        }}
      >
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-forge-card/80 text-forge-accent shadow-glow">
          <UploadCloud className="h-8 w-8" />
        </div>
        <h3 className="mt-4 text-lg font-semibold text-white">Drop your PDF here</h3>
        <p className="mt-2 text-sm text-slate-400">
          Files are stored in ephemeral container storage during Week 1.
        </p>
        <button
          type="button"
          className="mt-6 rounded-full bg-forge-accent px-6 py-3 text-sm font-semibold text-white shadow-glow"
          onClick={() => inputRef.current?.click()}
        >
          Choose File
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(event) => handleFiles(event.target.files)}
        />
        {status ? <p className="mt-4 text-xs text-slate-400">{status}</p> : null}
      </div>
    </div>
  );
}
