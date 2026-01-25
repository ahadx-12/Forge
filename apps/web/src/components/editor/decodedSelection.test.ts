import assert from "node:assert/strict";
import { test } from "node:test";

import { pickDecodedTextElementsWithFallback, type BBox } from "./decodedHitTest";

const viewportSize = { width: 1000, height: 1000 };

test("pickDecodedTextElementsWithFallback selects overlapping text elements", () => {
  const elements = [
    { id: "a", kind: "text_run", bbox_norm: [0.1, 0.1, 0.2, 0.2] as BBox },
    { id: "b", kind: "text_run", bbox_norm: [0.25, 0.1, 0.35, 0.2] as BBox },
    { id: "c", kind: "text_run", bbox_norm: [0.6, 0.1, 0.7, 0.2] as BBox }
  ];
  const region: BBox = [0.05, 0.05, 0.4, 0.25];
  const picked = pickDecodedTextElementsWithFallback(elements, region, { viewportSize });
  assert.deepEqual(
    picked.map((item) => item.id).sort(),
    ["a", "b"]
  );
});

test("pickDecodedTextElementsWithFallback falls back to nearest text element", () => {
  const elements = [
    { id: "near", kind: "text_run", bbox_norm: [0.48, 0.48, 0.52, 0.52] as BBox },
    { id: "far", kind: "text_run", bbox_norm: [0.8, 0.8, 0.9, 0.9] as BBox }
  ];
  const region: BBox = [0.51, 0.51, 0.53, 0.53];
  const picked = pickDecodedTextElementsWithFallback(elements, region, {
    viewportSize,
    nearestDistancePx: 40
  });
  assert.equal(picked.length, 1);
  assert.equal(picked[0].id, "near");
});

test("pickDecodedTextElementsWithFallback returns empty when no text is nearby", () => {
  const elements = [{ id: "far", kind: "text_run", bbox_norm: [0.8, 0.8, 0.9, 0.9] as BBox }];
  const region: BBox = [0.05, 0.05, 0.1, 0.1];
  const picked = pickDecodedTextElementsWithFallback(elements, region, {
    viewportSize,
    nearestDistancePx: 10
  });
  assert.equal(picked.length, 0);
});
