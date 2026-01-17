const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface DocumentMeta {
  doc_id: string;
  filename: string;
  size_bytes: number;
  created_at: string;
}

export interface DecodePageItem {
  kind: "text" | "path";
  bbox: number[];
  text?: string;
  font?: string | null;
  size?: number | null;
  color?: number | string | null;
  stroke_width?: number | null;
  stroke_color?: number | string | null;
  fill_color?: number | string | null;
}

export interface DecodePage {
  page_index: number;
  width_pt: number;
  height_pt: number;
  rotation: number;
  items: DecodePageItem[];
}

export interface DecodeResponse {
  doc_id: string;
  page_count: number;
  pages: DecodePage[];
}

export async function uploadDocument(file: File): Promise<DocumentMeta> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${baseUrl}/v1/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Upload failed");
  }

  return response.json();
}

export async function getDocumentMeta(docId: string): Promise<DocumentMeta> {
  const response = await fetch(`${baseUrl}/v1/documents/${docId}`);
  if (!response.ok) {
    throw new Error("Failed to load document metadata");
  }
  return response.json();
}

export async function getDecode(docId: string): Promise<DecodeResponse> {
  const response = await fetch(`${baseUrl}/v1/decode/${docId}`);
  if (!response.ok) {
    throw new Error("Failed to decode document");
  }
  return response.json();
}

export function getDownloadUrl(docId: string): string {
  return `${baseUrl}/v1/documents/${docId}/download`;
}
