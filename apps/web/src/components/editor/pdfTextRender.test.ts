import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPdfJsFontMap,
  deriveFontSizePxFromTransform,
  getPdfJsFontFamily,
  isPdfFontAvailable,
  normalizePdfJsTextTransform
} from "./pdfTextRender";

test("deriveFontSizePxFromTransform returns primary scale", () => {
  const size = deriveFontSizePxFromTransform([12, 0, 0, 12, 10, 20]);
  assert.equal(size, 12);
});

test("normalizePdfJsTextTransform normalizes matrix and preserves translation", () => {
  const normalized = normalizePdfJsTextTransform([10, 0, 0, 10, 5, 7]);
  assert.deepEqual(normalized, {
    fontSizePx: 10,
    matrix: [1, 0, 0, 1, 5, 7]
  });
});

test("buildPdfJsFontMap and getPdfJsFontFamily map font names", () => {
  const map = buildPdfJsFontMap({ F1: { fontFamily: "Helvetica" } });
  assert.equal(getPdfJsFontFamily("F1", map), "Helvetica");
  assert.equal(getPdfJsFontFamily("Missing", map), null);
});

test("isPdfFontAvailable checks mapped values", () => {
  const map = buildPdfJsFontMap({ F1: { fontFamily: "\"Times New Roman\", serif" } });
  assert.equal(isPdfFontAvailable("Times New Roman", map), true);
  assert.equal(isPdfFontAvailable("Helvetica", map), false);
});
