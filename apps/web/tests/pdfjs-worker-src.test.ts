import assert from "node:assert/strict";
import { test } from "node:test";

import { getPdfWorkerSrc } from "../src/lib/pdfjs";

test("pdfjs worker src points to the public worker path", () => {
  const workerSrc = getPdfWorkerSrc();

  assert.equal(
    workerSrc,
    "/pdf.worker.min.mjs",
    "worker src should reference the public PDF.js worker path"
  );
});
