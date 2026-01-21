import assert from "node:assert/strict";
import test from "node:test";

import { normalizeBbox } from "@/components/editor/pdfJsGeometry";

test("normalizeBbox clamps to viewport bounds", () => {
  const bbox = normalizeBbox(
    { left: -10, top: 20, width: 120, height: 50 },
    100,
    200
  );

  assert.deepEqual(bbox, [0, 0.1, 1, 0.35]);
});
