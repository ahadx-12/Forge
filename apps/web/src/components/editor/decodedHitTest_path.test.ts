import assert from "node:assert/strict";
import { test } from "node:test";

import { pickDecodedElementsInRegion, type BBox } from "./decodedHitTest";

test("pickDecodedElementsInRegion includes path elements by default", () => {
  const elements = [
    { id: "path-1", kind: "path", bbox_norm: [0.2, 0.2, 0.4, 0.3] as BBox },
    { id: "text-1", kind: "text_run", bbox_norm: [0.6, 0.2, 0.8, 0.3] as BBox }
  ];
  const region: BBox = [0.15, 0.15, 0.45, 0.35];
  const picked = pickDecodedElementsInRegion(elements, region);
  assert.equal(picked.length, 1);
  assert.equal(picked[0].id, "path-1");
});
