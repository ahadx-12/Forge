import type {
  ForgeOverlayCommitRequest,
  ForgeOverlayCommitResponse,
  ForgeOverlayPatchOp,
  ForgeOverlayResponse,
  ForgeOverlaySelection
} from "./api";
import { ApiError } from "./api";

type CommitOverlayPatch = (docId: string, payload: ForgeOverlayCommitRequest) => Promise<ForgeOverlayCommitResponse>;
type FetchOverlay = (docId: string, pageIndex: number) => Promise<ForgeOverlayResponse>;

type PatchConflictDetails = {
  resolvedElementId?: string;
  currentContentHash?: string;
};

export type OverlayCommitRetryResult = {
  response: ForgeOverlayCommitResponse;
  selection: ForgeOverlaySelection[];
  refreshedOverlay?: ForgeOverlayResponse;
};

function parsePatchConflictDetails(error: unknown): PatchConflictDetails | null {
  if (!(error instanceof ApiError)) {
    return null;
  }
  if (error.status !== 409 || error.code !== "PATCH_CONFLICT") {
    return null;
  }
  const details = error.details ?? {};
  if (typeof details !== "object" || details === null) {
    return {};
  }
  return {
    resolvedElementId:
      typeof details.resolved_element_id === "string" ? details.resolved_element_id : undefined,
    currentContentHash:
      typeof details.current_content_hash === "string" ? details.current_content_hash : undefined
  };
}

export async function commitOverlayWithRetry(options: {
  docId: string;
  pageIndex: number;
  selection: ForgeOverlaySelection[];
  ops: ForgeOverlayPatchOp[];
  commitOverlayPatch: CommitOverlayPatch;
  fetchOverlay: FetchOverlay;
}): Promise<OverlayCommitRetryResult> {
  const { docId, pageIndex, selection, ops, commitOverlayPatch, fetchOverlay } = options;
  if (selection.length === 0) {
    throw new Error("Selection is required to commit overlay changes.");
  }
  const attemptCommit = (nextSelection: ForgeOverlaySelection[]) =>
    commitOverlayPatch(docId, {
      doc_id: docId,
      page_index: pageIndex,
      selection: nextSelection,
      ops
    });

  try {
    const response = await attemptCommit(selection);
    return { response, selection };
  } catch (error) {
    const conflict = parsePatchConflictDetails(error);
    if (!conflict) {
      throw error;
    }
    const refreshedOverlay = await fetchOverlay(docId, pageIndex);
    const baseSelection = selection[0];
    const resolvedElementId = conflict.resolvedElementId ?? baseSelection.element_id;
    const refreshedEntry = refreshedOverlay.overlay.find((entry) => entry.element_id === resolvedElementId);
    const nextHash =
      conflict.currentContentHash ?? refreshedEntry?.content_hash ?? baseSelection.content_hash;
    const nextText = refreshedEntry?.text ?? baseSelection.text;
    const retrySelection = selection.map((item) => ({
      ...item,
      element_id: resolvedElementId,
      content_hash: nextHash,
      text: nextText
    }));
    const response = await attemptCommit(retrySelection);
    return { response, selection: retrySelection, refreshedOverlay };
  }
}
