import assert from "node:assert/strict";
import { test } from "node:test";

import { createBBoxConverter } from "./overlayGeometry";

test("createBBoxConverter uses normalized coords without flipping when centered high", () => {
  const { toPixelRect, shouldFlipY } = createBBoxConverter(
    [[0.1, 0.1, 0.2, 0.2]],
    {
      containerWidth: 1000,
      containerHeight: 1000
    }
  );

  const rect = toPixelRect([0.1, 0.1, 0.2, 0.2]);
  assert.equal(shouldFlipY, false);
  assert.equal(rect.left, 100);
  assert.equal(rect.top, 100);
  assert.equal(rect.width, 100);
  assert.equal(rect.height, 100);
});

test("createBBoxConverter flips normalized coords when centers skew high", () => {
  const { toPixelRect, shouldFlipY } = createBBoxConverter(
    [[0.1, 0.8, 0.2, 0.9]],
    {
      containerWidth: 1000,
      containerHeight: 1000
    }
  );

  const rect = toPixelRect([0.1, 0.8, 0.2, 0.9]);
  assert.equal(shouldFlipY, true);
  assert.ok(Math.abs(rect.left - 100) < 0.001);
  assert.ok(Math.abs(rect.top - 100) < 0.001);
  assert.ok(Math.abs(rect.width - 100) < 0.001);
  assert.ok(Math.abs(rect.height - 100) < 0.001);
});

test("createBBoxConverter handles PDF point space with flip", () => {
  const { toPixelRect, shouldFlipY } = createBBoxConverter(
    [[0, 700, 100, 750]],
    {
      containerWidth: 600,
      containerHeight: 800,
      pageWidthPt: 600,
      pageHeightPt: 800
    }
  );

  const rect = toPixelRect([0, 700, 100, 750]);
  assert.equal(shouldFlipY, true);
  assert.equal(rect.left, 0);
  assert.equal(rect.top, 50);
  assert.equal(rect.width, 100);
  assert.equal(rect.height, 50);
});

test("createBBoxConverter handles image pixel space", () => {
  const { toPixelRect } = createBBoxConverter(
    [[100, 100, 200, 200]],
    {
      containerWidth: 600,
      containerHeight: 800,
      imageWidthPx: 1200,
      imageHeightPx: 1600
    }
  );

  const rect = toPixelRect([100, 100, 200, 200]);
  assert.equal(rect.left, 50);
  assert.equal(rect.top, 50);
  assert.equal(rect.width, 50);
  assert.equal(rect.height, 50);
});
