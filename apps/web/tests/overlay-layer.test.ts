import assert from "node:assert/strict";
import { test } from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { computeOverlayScale } from "../src/lib/overlay";
import { OverlayLayerStack } from "../src/components/editor/OverlayLayerStack";

const baseItem = {
  forge_id: "p0_t0",
  text: "Hello",
  bbox: [0, 0, 40, 12],
  font: "Helvetica",
  size: 12,
  color: "#000000",
  content_hash: "hash"
};

test("computeOverlayScale uses natural vs client dimensions", () => {
  const result = computeOverlayScale({
    naturalWidth: 200,
    naturalHeight: 100,
    clientWidth: 100,
    clientHeight: 50
  });
  assert.equal(result.scaleX, 0.5);
  assert.equal(result.scaleY, 0.5);
});

test("overlay masks render before text layer", () => {
  const markup = renderToStaticMarkup(
    React.createElement(OverlayLayerStack, {
      pageIndex: 0,
      items: [baseItem],
      overlayMap: {},
      masks: [{ bbox_px: [0, 0, 40, 12], color: "#ffffff" }],
      selectedForgeId: null,
      showDebugOverlay: false,
      debugLimit: 0,
      onSelect: () => undefined
    })
  );

  const maskIndex = markup.indexOf("data-layer=\"masks\"");
  const textIndex = markup.indexOf("data-layer=\"text\"");
  assert.ok(maskIndex !== -1, "mask layer is present");
  assert.ok(textIndex !== -1, "text layer is present");
  assert.ok(maskIndex < textIndex, "mask layer should render before text layer");
});
