import { copyFile, mkdir } from "node:fs/promises";
import { join } from "node:path";

const workerSource = join(
  process.cwd(),
  "node_modules",
  "pdfjs-dist",
  "legacy",
  "build",
  "pdf.worker.min.mjs"
);

const publicDir = join(process.cwd(), "public");
const workerTarget = join(publicDir, "pdf.worker.min.mjs");

await mkdir(publicDir, { recursive: true });
await copyFile(workerSource, workerTarget);

console.log("Copied pdf.worker.min.mjs to public/");
