"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { FileUp, FolderPlus } from "lucide-react";
import { useDropzone } from "react-dropzone";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { uploadDocument } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (file: File) => {
    setError(null);
    setIsUploading(true);
    try {
      const response = await uploadDocument(file);
      router.push(`/editor/${response.doc_id}`);
    } catch (err) {
      setError("Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const dropzone = useDropzone({
    accept: { "application/pdf": [".pdf"] },
    multiple: false,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles[0]) {
        void handleUpload(acceptedFiles[0]);
      }
    },
  });

  const dropzoneClasses = useMemo(
    () =>
      dropzone.isDragActive
        ? "border-accent-400 bg-ink-800/80"
        : "border-ink-600 bg-ink-900/70",
    [dropzone.isDragActive]
  );

  return (
    <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
      <Card className="relative overflow-hidden">
        <CardHeader>
          <CardTitle>New Project</CardTitle>
          <CardDescription>Upload a PDF to start a new editing session.</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            {...dropzone.getRootProps()}
            className={`flex flex-col items-center gap-4 rounded-3xl border border-dashed px-6 py-10 text-center transition ${dropzoneClasses}`}
          >
            <input {...dropzone.getInputProps()} />
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-ink-700">
              <FileUp className="h-6 w-6 text-frost-100" />
            </div>
            <div>
              <p className="text-sm font-medium">Drag a PDF here or browse</p>
              <p className="text-xs text-frost-200/70">Multi-page PDFs supported</p>
            </div>
            <label className="cursor-pointer">
              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    void handleUpload(file);
                  }
                }}
              />
              <Button size="sm" disabled={isUploading}>
                {isUploading ? "Uploading..." : "Choose file"}
              </Button>
            </label>
            {error ? <p className="text-xs text-red-300">{error}</p> : null}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Project Status</CardTitle>
          <CardDescription>Week 1: upload and editor foundation.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 text-sm text-frost-200/80">
            <div className="flex items-center gap-3">
              <FolderPlus className="h-4 w-4" />
              <span>Projects stored locally during development.</span>
            </div>
            <div className="rounded-2xl border border-ink-700 bg-ink-900/70 px-4 py-3 text-xs">
              Use Railway environment variables to connect web and api deployments.
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
