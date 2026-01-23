import assert from "node:assert/strict";
import { test } from "node:test";

import { clampBBox, pickDecodedElementsInRegion, type BBox } from "./decodedHitTest";

test("pickDecodedElementsInRegion selects multiple elements", () => {
  const elements = [
    { id: "a", kind: "text_run", bbox_norm: [0.1, 0.1, 0.2, 0.2] as BBox },
    { id: "b", kind: "text_run", bbox_norm: [0.3, 0.1, 0.4, 0.2] as BBox }
  ];
  const region: BBox = [0.05, 0.05, 0.45, 0.25];
  const picked = pickDecodedElementsInRegion(elements, region);
  assert.deepEqual(
    picked.map((item) => item.id),
    ["a", "b"]
  );
});

test("pickDecodedElementsInRegion uses overlap ratio to prefer small targets", () => {
  const elements = [
    { id: "small", kind: "text_run", bbox_norm: [0.1, 0.1, 0.15, 0.15] as BBox },
    { id: "large", kind: "text_run", bbox_norm: [0.1, 0.1, 0.4, 0.4] as BBox }
  ];
  const region: BBox = [0.09, 0.09, 0.16, 0.16];
  const picked = pickDecodedElementsInRegion(elements, region);
  assert.equal(picked[0].id, "small");
});

test("pickDecodedElementsInRegion sorts by overlap ratio then area then id", () => {
  const elements = [
    { id: "b", kind: "text_run", bbox_norm: [0.1, 0.1, 0.3, 0.3] as BBox },
    { id: "a", kind: "text_run", bbox_norm: [0.1, 0.1, 0.3, 0.3] as BBox }
  ];
  const region: BBox = [0.1, 0.1, 0.3, 0.3];
  const picked = pickDecodedElementsInRegion(elements, region);
  assert.equal(picked.length, 2);
  assert.deepEqual(
    picked.map((item) => item.id),
    ["a", "b"]
  );
});

test("clampBBox constrains values to 0..1", () => {
  assert.deepEqual(clampBBox([-0.2, 1.2, 0.8, 0.9]), [0, 0.9, 0.8, 1]);
});
