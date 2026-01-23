import assert from "node:assert/strict";
import { test } from "node:test";

import type { ForgeOverlayCommitRequest, ForgeOverlayCommitResponse, ForgeOverlayResponse } from "./api";
import { ApiError } from "./api";
import { commitOverlayWithRetry } from "./overlay-commit";

test("commitOverlayWithRetry retries with server-provided content hash", async () => {
  const calls: ForgeOverlayCommitRequest[] = [];
  const commitOverlayPatch = async (_docId: string, payload: ForgeOverlayCommitRequest) => {
    calls.push(payload);
    if (calls.length === 1) {
      throw new ApiError("Conflict", 409, "PATCH_CONFLICT", "req-1", {
        resolved_element_id: "el-1",
        current_content_hash: "server-hash"
      });
    }
    return {
      patchset: {
        patch_id: "patch-1",
        created_at_iso: new Date().toISOString(),
        ops: payload.ops
      },
      overlay: [
        {
          element_id: "el-1",
          text: "Updated",
          content_hash: "new-hash"
        }
      ],
      masks: []
    } satisfies ForgeOverlayCommitResponse;
  };

  const fetchOverlay = async (_docId: string, _pageIndex: number): Promise<ForgeOverlayResponse> => ({
    doc_id: "doc-1",
    page_index: 0,
    overlay: [
      {
        element_id: "el-1",
        text: "Refreshed",
        content_hash: "overlay-hash"
      }
    ],
    masks: []
  });

  await commitOverlayWithRetry({
    docId: "doc-1",
    pageIndex: 0,
    selection: [
      {
        element_id: "el-1",
        text: "Original",
        content_hash: "old-hash",
        bbox: [0, 0, 1, 1],
        element_type: "text"
      }
    ],
    ops: [
      {
        type: "replace_element",
        element_id: "el-1",
        old_text: "Original",
        new_text: "Updated"
      }
    ],
    commitOverlayPatch,
    fetchOverlay
  });

  assert.equal(calls.length, 2);
  assert.equal(calls[1]?.selection[0]?.content_hash, "server-hash");
});
