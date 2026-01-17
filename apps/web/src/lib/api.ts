export type DocumentMeta = {
  doc_id: string;
  filename: string;
  size_bytes: number;
  created_at_iso: string;
};

export type DecodePageItem = {
  kind: "text" | "drawing";
  bbox: number[];
  text?: string;
  font?: string;
  size?: number;
  color?: number | null;
  width?: number;
  fill?: number | null;
};

export type DecodePage = {
  index: number;
  width_pt: number;
  height_pt: number;
  rotation: number;
  items: DecodePageItem[];
};

export type DecodePayload = {
  doc_id: string;
  page_count: number;
  pages: DecodePage[];
  extracted_at_iso: string;
};

export type IRPrimitive = {
  id: string;
  kind: "text" | "path";
  bbox: number[];
  z_index: number;
  style: Record<string, unknown>;
  signature_fields: Record<string, unknown>;
  text?: string | null;
};

export type IRPage = {
  doc_id: string;
  page_index: number;
  width_pt: number;
  height_pt: number;
  rotation: number;
  primitives: IRPrimitive[];
};

export type HitTestPoint = {
  x: number;
  y: number;
};

export type HitTestRect = {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
};

export type HitTestRequest = {
  point?: HitTestPoint;
  rect?: HitTestRect;
};

export type HitTestCandidate = {
  id: string;
  score: number;
  bbox: number[];
  kind: "text" | "path";
};

export type HitTestResponse = {
  doc_id: string;
  page_index: number;
  candidates: HitTestCandidate[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function downloadUrl(docId: string): string {
  return `${API_BASE}/v1/documents/${docId}/download`;
}

export async function uploadDocument(file: File): Promise<DocumentMeta> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/v1/documents/upload`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    throw new Error("Upload failed");
  }
  const payload = await response.json();
  return payload.document as DocumentMeta;
}

export async function getDocumentMeta(docId: string): Promise<DocumentMeta> {
  const response = await fetch(`${API_BASE}/v1/documents/${docId}`);
  if (!response.ok) {
    throw new Error("Failed to load document metadata");
  }
  return (await response.json()) as DocumentMeta;
}

export async function getDecode(docId: string): Promise<DecodePayload> {
  const response = await fetch(`${API_BASE}/v1/decode/${docId}`);
  if (!response.ok) {
    throw new Error("Failed to load decode data");
  }
  return (await response.json()) as DecodePayload;
}

export async function getIR(docId: string, pageIndex: number): Promise<IRPage> {
  const response = await fetch(`${API_BASE}/v1/ir/${docId}?page=${pageIndex}`);
  if (!response.ok) {
    throw new Error("Failed to load IR data");
  }
  return (await response.json()) as IRPage;
}

export async function hitTest(
  docId: string,
  pageIndex: number,
  payload: HitTestRequest
): Promise<HitTestResponse> {
  const response = await fetch(`${API_BASE}/v1/hittest/${docId}?page=${pageIndex}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error("Failed to hit-test");
  }
  return (await response.json()) as HitTestResponse;
}
