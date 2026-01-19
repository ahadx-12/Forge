import { access, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, "..");
const workerPath = path.join(appRoot, "public", "pdf.worker.min.mjs");

async function verifyWorker() {
  await access(workerPath);
  const { size } = await stat(workerPath);
  if (size === 0) {
    throw new Error(`PDF.js worker at ${workerPath} is empty.`);
  }
  console.log(`Verified PDF.js worker exists at ${workerPath} (${size} bytes).`);
}

verifyWorker().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
