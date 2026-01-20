import assert from "node:assert/strict";
import { test } from "node:test";

import { getPageCanvasSize, normalizedToPixelRect } from "./pageCanvas";

test("getPageCanvasSize clamps to configured bounds", () => {
  const size = getPageCanvasSize(1200, 600, 900);
  assert.equal(size.width, 900);
  assert.equal(size.height, 1350);

  const small = getPageCanvasSize(200, 600, 900);
  assert.equal(small.width, 320);
  assert.equal(small.height, 480);
});

test("normalizedToPixelRect maps top-left normalized bbox", () => {
  const rect = normalizedToPixelRect([0.1, 0.2, 0.4, 0.6], { width: 1000, height: 2000 });
  assert.equal(rect.left, 100);
  assert.equal(rect.top, 400);
  assert.ok(Math.abs(rect.width - 300) < 0.001);
  assert.ok(Math.abs(rect.height - 800) < 0.001);
});
