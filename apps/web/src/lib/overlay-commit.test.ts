import assert from "node:assert/strict";
import { test } from "node:test";

import type {
  ForgeOverlayCommitRequest,
  ForgeOverlayCommitResponse,
  ForgeOverlayPlanRequest,
  ForgeOverlayPlanResponse,
  ForgeOverlayResponse
} from "./api";
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
    masks: [],
    overlay_version: 1
  });

  await commitOverlayWithRetry({
    docId: "doc-1",
    pageIndex: 0,
    baseOverlayVersion: 1,
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

test("commitOverlayWithRetry replans after overlay version conflict", async () => {
  const commitCalls: ForgeOverlayCommitRequest[] = [];
  const planCalls: number[] = [];
  const commitOverlayPatch = async (_docId: string, payload: ForgeOverlayCommitRequest) => {
    commitCalls.push(payload);
    if (commitCalls.length === 1) {
      throw new ApiError("Conflict", 409, "PATCH_CONFLICT", "req-2", {
        current_overlay_version: 2
      });
    }
    return {
      patchset: {
        patch_id: "patch-2",
        created_at_iso: new Date().toISOString(),
        ops: payload.ops
      },
      overlay: [
        {
          element_id: "el-2",
          text: "Updated",
          content_hash: "new-hash"
        }
      ],
      masks: [],
      overlay_version: 2
    } satisfies ForgeOverlayCommitResponse;
  };
  const fetchOverlay = async (_docId: string, _pageIndex: number): Promise<ForgeOverlayResponse> => ({
    doc_id: "doc-2",
    page_index: 0,
    overlay: [
      {
        element_id: "el-2",
        text: "Refreshed",
        content_hash: "overlay-hash"
      }
    ],
    masks: [],
    overlay_version: 2
  });
  const planOverlayPatch = async (payload: { base_overlay_version?: number }) => {
    planCalls.push(payload.base_overlay_version ?? 0);
    return {
      schema_version: 2,
      ops: [
        {
          type: "replace_element",
          element_id: "el-2",
          old_text: "Original",
          new_text: "Updated",
          preserve_style: true,
          preserve_position: true,
          preserve_font_size: true,
          preserve_color: true
        }
      ]
    };
  };

  await commitOverlayWithRetry({
    docId: "doc-2",
    pageIndex: 0,
    baseOverlayVersion: 1,
    selection: [
      {
        element_id: "el-2",
        text: "Original",
        content_hash: "old-hash",
        bbox: [0, 0, 1, 1],
        element_type: "text"
      }
    ],
    ops: [
      {
        type: "replace_element",
        element_id: "el-2",
        old_text: "Original",
        new_text: "Updated"
      }
    ],
    commitOverlayPatch,
    fetchOverlay,
    planOverlayPatch: planOverlayPatch as (payload: ForgeOverlayPlanRequest) => Promise<ForgeOverlayPlanResponse>,
    planRequest: {
      doc_id: "doc-2",
      page_index: 0,
      selection: [
        {
          element_id: "el-2",
          text: "Original",
          content_hash: "old-hash",
          bbox: [0, 0, 1, 1],
          element_type: "text"
        }
      ],
      user_prompt: "Update text"
    }
  });

  assert.equal(commitCalls.length, 2);
  assert.equal(planCalls.length, 1);
  assert.equal(commitCalls[1]?.base_overlay_version, 2);
});
