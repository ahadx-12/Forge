import assert from "node:assert/strict";
import { test } from "node:test";

import { getPdfWorkerSrc } from "../src/lib/pdfjs";

test("pdfjs worker src is derived from the pdfjs-dist package", () => {
  const workerSrc = getPdfWorkerSrc();

  assert.ok(
    workerSrc.includes("pdfjs-dist/build/pdf.worker.min.mjs"),
    "worker src should reference the bundled pdfjs-dist worker"
  );
  assert.ok(
    !workerSrc.includes("/public/"),
    "worker src should not point at a copied public worker file"
  );
});
