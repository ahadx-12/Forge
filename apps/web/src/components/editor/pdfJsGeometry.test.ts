import assert from "node:assert/strict";
import test from "node:test";

import { createHash } from "node:crypto";

import {
  buildContentHash,
  buildElementId,
  hitTestSmallest,
  normalizeBbox,
  roundNormalizedBbox
} from "@/components/editor/pdfJsGeometry";

test("normalizeBbox clamps to viewport bounds", () => {
  const bbox = normalizeBbox(
    { left: -10, top: 20, width: 120, height: 50 },
    100,
    200
  );

  assert.deepEqual(bbox, [0, 0.1, 1, 0.35]);
});

test("normalizeBbox stays stable across scale", () => {
  const base = normalizeBbox({ left: 10, top: 20, width: 30, height: 40 }, 100, 200);
  const scaled = normalizeBbox({ left: 20, top: 40, width: 60, height: 80 }, 200, 400);

  assert.deepEqual(roundNormalizedBbox(base, 4), roundNormalizedBbox(scaled, 4));
});

test("hitTestSmallest picks smallest bbox when overlapping", () => {
  const bboxes = [
    { bbox: [0.1, 0.1, 0.9, 0.9] as const },
    { bbox: [0.2, 0.2, 0.3, 0.3] as const }
  ];
  const hit = hitTestSmallest(bboxes, { x: 0.25, y: 0.25 }, { x: 0, y: 0 });

  assert.equal(hit, 1);
});

test("element_id and content_hash are deterministic", () => {
  const text = "Hello";
  const bbox = [0.1, 0.2, 0.3, 0.4] as const;
  const styleKey = "FontA|12";
  const bboxString = "0.1000,0.2000,0.3000,0.4000";
  const signature = `${text}|${bboxString}|${styleKey}`;
  const sha1 = createHash("sha1").update(signature).digest("hex").slice(0, 8);
  const sha256 = createHash("sha256").update(signature).digest("hex").slice(0, 16);

  assert.equal(buildElementId(2, text, bbox, styleKey), `p2_${sha1}`);
  assert.equal(buildContentHash(text, bbox, styleKey), sha256);
});
