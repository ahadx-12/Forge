import assert from "node:assert/strict";
import { test } from "node:test";

import { getPageCanvasSize, normalizedToPixelRect, pixelRectToNormalizedBBox } from "./pageCanvas";

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

test("pixelRectToNormalizedBBox preserves top-left origin", () => {
  const bbox = pixelRectToNormalizedBBox(
    { left: 100, top: 50, width: 800, height: 200 },
    { width: 1000, height: 2000 }
  );
  assert.deepEqual(bbox, [0.1, 0.025, 0.9, 0.125]);
});

test("pixelRectToNormalizedBBox round-trips with normalizedToPixelRect", () => {
  const pageSize = { width: 1000, height: 2000 };
  const bbox: [number, number, number, number] = [0.12, 0.08, 0.8, 0.4];
  const rect = normalizedToPixelRect(bbox, pageSize);
  const roundTrip = pixelRectToNormalizedBBox(rect, pageSize);
  assert.deepEqual(roundTrip, bbox);
});
