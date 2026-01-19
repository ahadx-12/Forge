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
  patch_meta?: Record<string, unknown> | null;
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

export type PatchOp =
  | {
      op: "set_style";
      target_id: string;
      stroke_color?: number[] | number | null;
      stroke_width_pt?: number | null;
      fill_color?: number[] | number | null;
      opacity?: number | null;
    }
  | {
      op: "replace_text";
      target_id: string;
      new_text: string;
      policy: "FIT_IN_BOX" | "OVERFLOW_NOTICE";
    };

export type PatchsetInput = {
  ops: PatchOp[];
  page_index: number;
  selected_ids?: string[] | null;
  rationale_short?: string | null;
};

export type PatchsetRecord = {
  patchset_id: string;
  created_at_iso: string;
  ops: PatchOp[];
  page_index: number;
  rationale_short?: string | null;
  selected_ids?: string[] | null;
  diff_summary: {
    target_id: string;
    changed_fields: string[];
    geometry_changed: boolean;
  }[];
  results: {
    target_id: string;
    applied_font_size_pt?: number | null;
    overflow?: boolean | null;
  }[];
};

export type PatchsetListResponse = {
  doc_id: string;
  patchsets: PatchsetRecord[];
};

export type PatchCommitResponse = {
  patchset: PatchsetRecord;
  patch_log: PatchsetRecord[];
};

export type PatchPlanResponse = {
  proposed_patchset: {
    patchset_id: string;
    ops: PatchOp[];
    rationale_short: string;
    page_index: number;
  };
};

export type ExportMaskMode = "SOLID" | "AUTO_BG";

const RAW_API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;
const API_BASE = (RAW_API_BASE && RAW_API_BASE.trim().length > 0 ? RAW_API_BASE : "http://localhost:8000")
  .replace(/\/+$/, "");

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const payload = await response.json();
    if (payload && typeof payload.detail === "string") {
      return payload.detail;
    }
    if (payload && typeof payload.error === "string") {
      return payload.error;
    }
  } catch (error) {
    return null;
  }
  return null;
}

export function apiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${normalized}`;
}

export function downloadUrl(docId: string): string {
  return apiUrl(`/v1/documents/${docId}/download`);
}

export function exportPdfUrl(docId: string, maskMode?: ExportMaskMode): string {
  if (maskMode) {
    const params = new URLSearchParams({ mask_mode: maskMode });
    return apiUrl(`/v1/export/${docId}?${params.toString()}`);
  }
  return apiUrl(`/v1/export/${docId}`);
}

export async function uploadDocument(file: File): Promise<DocumentMeta> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(apiUrl("/v1/documents/upload"), {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ? `Upload failed: ${detail}` : "Upload failed");
  }
  const payload = await response.json();
  return payload.document as DocumentMeta;
}

export async function getDocumentMeta(docId: string): Promise<DocumentMeta> {
  const response = await fetch(apiUrl(`/v1/documents/${docId}`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ? `Failed to load document metadata: ${detail}` : "Failed to load document metadata");
  }
  return (await response.json()) as DocumentMeta;
}

export async function getDecode(docId: string): Promise<DecodePayload> {
  const response = await fetch(apiUrl(`/v1/decode/${docId}`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ? `Failed to load decode data: ${detail}` : "Failed to load decode data");
  }
  return (await response.json()) as DecodePayload;
}

export async function getIR(docId: string, pageIndex: number): Promise<IRPage> {
  const response = await fetch(apiUrl(`/v1/ir/${docId}?page=${pageIndex}`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ? `Failed to load IR data: ${detail}` : "Failed to load IR data");
  }
  return (await response.json()) as IRPage;
}

export async function getCompositeIR(docId: string, pageIndex: number): Promise<IRPage> {
  const response = await fetch(apiUrl(`/v1/composite/ir/${docId}?page=${pageIndex}`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ? `Failed to load composite IR data: ${detail}` : "Failed to load composite IR data");
  }
  return (await response.json()) as IRPage;
}

export async function hitTest(
  docId: string,
  pageIndex: number,
  payload: HitTestRequest
): Promise<HitTestResponse> {
  const response = await fetch(apiUrl(`/v1/hittest/${docId}?page=${pageIndex}`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ? `Failed to hit-test: ${detail}` : "Failed to hit-test");
  }
  return (await response.json()) as HitTestResponse;
}

export async function planPatch(payload: {
  doc_id: string;
  page_index: number;
  selected_ids: string[];
  user_instruction: string;
  candidates?: string[];
}): Promise<PatchPlanResponse> {
  const response = await fetch(apiUrl("/v1/ai/plan_patch"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ? `Failed to plan patch: ${detail}` : "Failed to plan patch");
  }
  return (await response.json()) as PatchPlanResponse;
}

export async function commitPatch(docId: string, patchset: PatchsetInput): Promise<PatchCommitResponse> {
  const response = await fetch(apiUrl("/v1/patch/commit"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      doc_id: docId,
      patchset
    })
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ? `Failed to commit patch: ${detail}` : "Failed to commit patch");
  }
  return (await response.json()) as PatchCommitResponse;
}

export async function getPatches(docId: string): Promise<PatchsetListResponse> {
  const response = await fetch(apiUrl(`/v1/patches/${docId}`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ? `Failed to load patch history: ${detail}` : "Failed to load patch history");
  }
  return (await response.json()) as PatchsetListResponse;
}

export async function revertLastPatch(docId: string): Promise<PatchsetListResponse> {
  const response = await fetch(apiUrl(`/v1/patch/revert_last?doc_id=${docId}`), {
    method: "POST"
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ? `Failed to revert patch: ${detail}` : "Failed to revert patch");
  }
  return (await response.json()) as PatchsetListResponse;
}
