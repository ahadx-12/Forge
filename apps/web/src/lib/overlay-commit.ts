import type {
  DecodedDocumentV1,
  ForgeDecodedSelection,
  ForgeOverlayCommitRequest,
  ForgeOverlayCommitResponse,
  ForgeOverlayPatchOp,
  ForgeOverlayPlanRequest,
  ForgeOverlayPlanResponse,
  ForgeOverlayResponse,
  ForgeOverlaySelection
} from "./api";
import { ApiError } from "./api";

type CommitOverlayPatch = (docId: string, payload: ForgeOverlayCommitRequest) => Promise<ForgeOverlayCommitResponse>;
type FetchOverlay = (docId: string, pageIndex: number) => Promise<ForgeOverlayResponse>;
type FetchDecoded = (docId: string) => Promise<DecodedDocumentV1>;
type PlanOverlayPatch = (payload: ForgeOverlayPlanRequest) => Promise<ForgeOverlayPlanResponse>;

type PatchConflictDetails = {
  resolvedElementId?: string;
  currentContentHash?: string;
  retryHint?: "refresh_overlay" | "refresh_decoded";
  currentEntry?: { elementId?: string; text?: string; contentHash?: string };
  currentOverlayVersion?: number;
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
  const currentEntry =
    typeof (details as { current_entry?: unknown }).current_entry === "object" &&
    (details as { current_entry?: unknown }).current_entry !== null
      ? ((details as { current_entry?: Record<string, unknown> }).current_entry as Record<string, unknown>)
      : null;
  return {
    resolvedElementId:
      typeof details.resolved_element_id === "string" ? details.resolved_element_id : undefined,
    currentContentHash:
      typeof details.current_content_hash === "string" ? details.current_content_hash : undefined,
    retryHint:
      details.retry_hint === "refresh_decoded" || details.retry_hint === "refresh_overlay"
        ? details.retry_hint
        : undefined,
    currentEntry: currentEntry
      ? {
          elementId: typeof currentEntry.element_id === "string" ? currentEntry.element_id : undefined,
          text: typeof currentEntry.text === "string" ? currentEntry.text : undefined,
          contentHash:
            typeof currentEntry.content_hash === "string" ? currentEntry.content_hash : undefined
        }
      : undefined,
    currentOverlayVersion:
      typeof details.current_overlay_version === "number" ? details.current_overlay_version : undefined
  };
}

export async function commitOverlayWithRetry(options: {
  docId: string;
  pageIndex: number;
  selection: ForgeOverlaySelection[];
  ops: ForgeOverlayPatchOp[];
  commitOverlayPatch: CommitOverlayPatch;
  fetchOverlay: FetchOverlay;
  baseOverlayVersion?: number;
  planOverlayPatch?: PlanOverlayPatch;
  planRequest?: Omit<ForgeOverlayPlanRequest, "base_overlay_version">;
  maxRetries?: number;
  decodedSelection?: ForgeDecodedSelection;
  fetchDecoded?: FetchDecoded;
}): Promise<OverlayCommitRetryResult> {
  const {
    docId,
    pageIndex,
    selection,
    ops,
    commitOverlayPatch,
    fetchOverlay,
    baseOverlayVersion,
    planOverlayPatch,
    planRequest,
    maxRetries = 2,
    decodedSelection,
    fetchDecoded
  } = options;
  if (selection.length === 0) {
    throw new Error("Selection is required to commit overlay changes.");
  }
  if (baseOverlayVersion === undefined || baseOverlayVersion === null) {
    throw new Error("Overlay version is required to commit overlay changes.");
  }

  let currentSelection = selection;
  let currentOps = ops;
  let currentBaseVersion = baseOverlayVersion;
  let refreshedOverlay: ForgeOverlayResponse | undefined;

  const attemptCommit = (nextSelection: ForgeOverlaySelection[], nextOps: ForgeOverlayPatchOp[]) =>
    commitOverlayPatch(docId, {
      doc_id: docId,
      page_index: pageIndex,
      base_overlay_version: currentBaseVersion,
      selection: nextSelection,
      ops: nextOps,
      decoded_selection: decodedSelection
    });

  // Optimistic concurrency: on version conflicts, re-fetch + (optionally) replan before retrying.
  for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
    try {
      const response = await attemptCommit(currentSelection, currentOps);
      return { response, selection: currentSelection, refreshedOverlay };
    } catch (error) {
      const conflict = parsePatchConflictDetails(error);
      if (!conflict) {
        throw error;
      }
      if (conflict.currentOverlayVersion !== undefined) {
        refreshedOverlay = await fetchOverlay(docId, pageIndex);
        currentBaseVersion = conflict.currentOverlayVersion ?? refreshedOverlay.overlay_version;
        if (planOverlayPatch && planRequest) {
          const plan = await planOverlayPatch({
            ...planRequest,
            base_overlay_version: currentBaseVersion
          });
          currentOps = plan.ops;
        }
        continue;
      }
      if (conflict.retryHint === "refresh_decoded" && fetchDecoded) {
        const refreshedDecoded = await fetchDecoded(docId);
        currentSelection = currentSelection.map((item) => {
          const page = refreshedDecoded.pages.find((entry) => entry.page_index === pageIndex);
          const match = page?.elements.find((element) => element.id === item.element_id);
          return match
            ? {
                ...item,
                text: match.text ?? item.text,
                content_hash: match.content_hash ?? item.content_hash,
                bbox: match.bbox_norm ?? item.bbox
              }
            : item;
        });
        continue;
      }
      refreshedOverlay = await fetchOverlay(docId, pageIndex);
      const baseSelection = currentSelection[0];
      const resolvedElementId = conflict.resolvedElementId ?? baseSelection.element_id;
      const refreshedEntry =
        refreshedOverlay.overlay.find((entry) => entry.element_id === resolvedElementId) ??
        (conflict.currentEntry?.elementId
          ? {
              element_id: conflict.currentEntry.elementId,
              text: conflict.currentEntry.text ?? baseSelection.text,
              content_hash: conflict.currentEntry.contentHash ?? baseSelection.content_hash
            }
          : undefined);
      const nextHash =
        conflict.currentContentHash ?? refreshedEntry?.content_hash ?? baseSelection.content_hash;
      const nextText = refreshedEntry?.text ?? baseSelection.text;
      currentSelection = currentSelection.map((item) => ({
        ...item,
        content_hash: nextHash,
        text: nextText
      }));
    }
  }

  throw new Error("Unable to apply overlay changes after retrying.");
}
