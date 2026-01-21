export type DocumentMeta = {
  doc_id: string;
  filename: string;
  size_bytes: number;
  created_at_iso: string;
  has_forge_manifest?: boolean;
  forge_manifest_url?: string | null;
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
  font_ref?: Record<string, unknown> | null;
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
      old_text?: string | null;
    };

export type SelectionFingerprint = {
  element_id: string;
  page_index: number;
  content_hash: string;
  bbox: number[];
  parent_id?: string | null;
};

export type SelectionSnapshot = {
  element_id: string;
  page_index: number;
  bbox: number[];
  text?: string | null;
  font_name?: string | null;
  font_size?: number | null;
  parent_id?: string | null;
  content_hash?: string | null;
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
    ok?: boolean;
    code?: string | null;
    details?: Record<string, unknown> | null;
    applied_font_size_pt?: number | null;
    overflow?: boolean | null;
    did_not_fit?: boolean | null;
    font_adjusted?: boolean | null;
    bbox_adjusted?: boolean | null;
    warnings?: Record<string, unknown>[];
  }[];
  warnings?: string[];
};

export type PatchsetListResponse = {
  doc_id: string;
  patchsets: PatchsetRecord[];
};

export type PatchCommitResponse = {
  patchset: PatchsetRecord;
  patch_log: PatchsetRecord[];
  applied_ops?: PatchsetRecord["results"];
  rejected_ops?: PatchsetRecord["results"];
};

export type PatchPlanResponse = {
  proposed_patchset: {
    schema_version: string;
    patchset_id: string;
    ops: PatchOp[];
    rationale_short: string;
    page_index: number;
  };
};

export type ExportMaskMode = "SOLID" | "AUTO_BG";

export type ForgeManifestElement = {
  element_id: string;
  element_type: "text" | "heading" | "list_item" | "table_cell";
  text: string;
  bbox: number[];
  style: {
    font_size_pt: number;
    is_bold: boolean;
    is_italic?: boolean;
    color: string;
    font_family: string;
    line_height?: number | null;
    wrap_policy?: "auto" | "nowrap" | "prewrap";
  };
  lines?: {
    text: string;
    bbox: number[];
    spans: {
      text: string;
      bbox: number[];
      style: {
        font_size_pt: number;
        font_family: string;
        is_bold: boolean;
        is_italic?: boolean;
        color: string;
      };
    }[];
  }[];
  page_index: number;
};

export type ForgeManifestPage = {
  page_index: number;
  width_pt: number;
  height_pt: number;
  width_px?: number;
  height_px?: number;
  rotation: number;
  image_path: string;
  elements: ForgeManifestElement[];
};

export type ForgeManifest = {
  doc_id: string;
  page_count: number;
  pages: ForgeManifestPage[];
  generated_at_iso: string;
};

export type ForgeOverlayEntry = {
  element_id: string;
  text: string;
  content_hash: string;
};

export type ForgeOverlayMask = {
  element_id?: string | null;
  bbox: number[];
  color: string;
};

export type ForgeOverlayResponse = {
  doc_id: string;
  page_index: number;
  overlay: ForgeOverlayEntry[];
  masks: ForgeOverlayMask[];
  page_image_width_px?: number;
  page_image_height_px?: number;
  pdf_box_width_pt?: number;
  pdf_box_height_pt?: number;
  rotation?: number;
  used_box?: string;
};

export type ForgeOverlaySelection = {
  element_id: string;
  text: string;
  content_hash: string;
  bbox: number[];
  element_type?: ForgeManifestElement["element_type"];
  style?: ForgeManifestElement["style"];
};

export type ForgeOverlayPatchOp = {
  type: "replace_element";
  element_id: string;
  old_text?: string | null;
  new_text: string;
  style_changes?: Record<string, unknown> | null;
};

export type ForgeOverlayPlanRequest = {
  doc_id: string;
  page_index: number;
  selection: ForgeOverlaySelection[];
  user_prompt: string;
};

export type ForgeOverlayPlanResponse = {
  schema_version: number;
  ops: ForgeOverlayPatchOp[];
  warnings?: string[];
};

export type ForgeOverlayCommitRequest = {
  doc_id: string;
  page_index: number;
  selection: ForgeOverlaySelection[];
  ops: ForgeOverlayPatchOp[];
};

export type ForgeOverlayCommitResponse = {
  patchset: {
    patch_id: string;
    created_at_iso: string;
    ops: ForgeOverlayPatchOp[];
  };
  overlay: ForgeOverlayEntry[];
  masks: ForgeOverlayMask[];
};

const RAW_API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;
const API_BASE = (RAW_API_BASE && RAW_API_BASE.trim().length > 0 ? RAW_API_BASE : "http://localhost:8000")
  .replace(/\/+$/, "");

async function readErrorDetail(
  response: Response
): Promise<{ message: string | null; code: string | null; request_id: string | null }> {
  try {
    const payload = await response.json();
    if (payload && typeof payload.detail === "string") {
      return { message: payload.detail, code: payload.error ?? null, request_id: payload.request_id ?? null };
    }
    if (payload && typeof payload.message === "string") {
      return { message: payload.message, code: payload.error ?? null, request_id: payload.request_id ?? null };
    }
    if (payload && typeof payload.error === "string") {
      return { message: payload.error, code: payload.error, request_id: payload.request_id ?? null };
    }
  } catch (error) {
    return { message: null, code: null, request_id: null };
  }
  return { message: null, code: null, request_id: null };
}

export function apiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${normalized}`;
}

export function downloadUrl(docId: string): string {
  return apiUrl(`/v1/documents/${docId}/download`);
}

export async function getDocumentFile(docId: string): Promise<ArrayBuffer> {
  const response = await fetch(apiUrl(`/v1/documents/${docId}/file`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail.message || "Unable to fetch document file.");
  }
  return response.arrayBuffer();
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
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(detail.message ? `Upload failed (${suffix}): ${detail.message}` : `Upload failed (${suffix})`);
  }
  const payload = await response.json();
  return payload.document as DocumentMeta;
}

export async function getDocumentMeta(docId: string): Promise<DocumentMeta> {
  const response = await fetch(apiUrl(`/v1/documents/${docId}`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(
      detail.message
        ? `Failed to load document metadata (${suffix}): ${detail.message}`
        : `Failed to load document metadata (${suffix})`
    );
  }
  return (await response.json()) as DocumentMeta;
}

export async function getForgeManifest(docId: string): Promise<ForgeManifest> {
  const response = await fetch(apiUrl(`/v1/documents/${docId}/forge/manifest`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(
      detail.message
        ? `Forge manifest failed (${suffix}): ${detail.message}`
        : `Forge manifest failed (${suffix})`
    );
  }
  return (await response.json()) as ForgeManifest;
}

export async function getForgeOverlay(docId: string, pageIndex: number): Promise<ForgeOverlayResponse> {
  const response = await fetch(apiUrl(`/v1/documents/${docId}/forge/overlay?page_index=${pageIndex}`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(
      detail.message ? `Forge overlay failed (${suffix}): ${detail.message}` : `Forge overlay failed (${suffix})`
    );
  }
  return (await response.json()) as ForgeOverlayResponse;
}

export async function planOverlayPatch(payload: ForgeOverlayPlanRequest): Promise<ForgeOverlayPlanResponse> {
  const response = await fetch(apiUrl("/v1/ai/plan_overlay_patch"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(detail.message ? `AI plan failed (${suffix}): ${detail.message}` : `AI plan failed (${suffix})`);
  }
  return (await response.json()) as ForgeOverlayPlanResponse;
}

export async function commitOverlayPatch(
  docId: string,
  payload: ForgeOverlayCommitRequest
): Promise<ForgeOverlayCommitResponse> {
  const response = await fetch(apiUrl(`/v1/documents/${docId}/forge/overlay/commit`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(
      detail.message ? `Overlay commit failed (${suffix}): ${detail.message}` : `Overlay commit failed (${suffix})`
    );
  }
  return (await response.json()) as ForgeOverlayCommitResponse;
}

export async function getDecode(docId: string): Promise<DecodePayload> {
  const response = await fetch(apiUrl(`/v1/decode/${docId}`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(
      detail.message ? `Failed to load decode data (${suffix}): ${detail.message}` : `Failed to load decode data (${suffix})`
    );
  }
  return (await response.json()) as DecodePayload;
}

export async function getIR(docId: string, pageIndex: number): Promise<IRPage> {
  const response = await fetch(apiUrl(`/v1/ir/${docId}?page=${pageIndex}`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(
      detail.message
        ? `Failed to load IR data (${suffix}): ${detail.message}`
        : `Failed to load IR data (${suffix})`
    );
  }
  return (await response.json()) as IRPage;
}

export async function getCompositeIR(docId: string, pageIndex: number): Promise<IRPage> {
  const response = await fetch(apiUrl(`/v1/composite/ir/${docId}?page=${pageIndex}`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(
      detail.message
        ? `Failed to load composite IR data (${suffix}): ${detail.message}`
        : `Failed to load composite IR data (${suffix})`
    );
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
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(
      detail.message ? `Failed to hit-test (${suffix}): ${detail.message}` : `Failed to hit-test (${suffix})`
    );
  }
  return (await response.json()) as HitTestResponse;
}

export async function planPatch(payload: {
  doc_id: string;
  page_index: number;
  selected_ids?: string[];
  user_instruction: string;
  candidates?: string[];
  selected_primitives?: {
    id: string;
    kind: "text" | "path";
    bbox: number[];
    text?: string | null;
    style?: Record<string, unknown>;
  }[];
  selection: SelectionSnapshot;
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
    const suffix = [response.status, detail.code, detail.request_id && `request_id=${detail.request_id}`]
      .filter(Boolean)
      .join(" ");
    throw new Error(
      detail.message ? `Failed to plan patch (${suffix}): ${detail.message}` : `Failed to plan patch (${suffix})`
    );
  }
  return (await response.json()) as PatchPlanResponse;
}

export async function commitPatch(
  docId: string,
  patchset: PatchsetInput,
  allowedTargets?: SelectionFingerprint[]
): Promise<PatchCommitResponse> {
  const response = await fetch(apiUrl("/v1/patch/commit"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      doc_id: docId,
      patchset,
      allowed_targets: allowedTargets
    })
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(
      detail.message ? `Failed to commit patch (${suffix}): ${detail.message}` : `Failed to commit patch (${suffix})`
    );
  }
  return (await response.json()) as PatchCommitResponse;
}

export async function getPatches(docId: string): Promise<PatchsetListResponse> {
  const response = await fetch(apiUrl(`/v1/patches/${docId}`));
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(
      detail.message
        ? `Failed to load patch history (${suffix}): ${detail.message}`
        : `Failed to load patch history (${suffix})`
    );
  }
  return (await response.json()) as PatchsetListResponse;
}

export async function revertLastPatch(docId: string): Promise<PatchsetListResponse> {
  const response = await fetch(apiUrl(`/v1/patch/revert_last?doc_id=${docId}`), {
    method: "POST"
  });
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    const suffix = [response.status, detail.code].filter(Boolean).join(" ");
    throw new Error(
      detail.message ? `Failed to revert patch (${suffix}): ${detail.message}` : `Failed to revert patch (${suffix})`
    );
  }
  return (await response.json()) as PatchsetListResponse;
}
