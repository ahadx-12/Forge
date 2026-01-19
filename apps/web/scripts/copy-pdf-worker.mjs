import { access, copyFile, mkdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, "..");
const publicDir = path.join(appRoot, "public");
const destination = path.join(publicDir, "pdf.worker.min.mjs");

const workerCandidates = [
  path.join(appRoot, "node_modules", "pdfjs-dist", "build", "pdf.worker.min.mjs"),
  path.join(appRoot, "node_modules", "pdfjs-dist", "build", "pdf.worker.min.js")
];

async function findWorkerSource() {
  for (const candidate of workerCandidates) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      continue;
    }
  }
  throw new Error(
    `Unable to locate the PDF.js worker. Looked in:\n${workerCandidates
      .map((candidate) => `- ${candidate}`)
      .join("\n")}`
  );
}

async function copyWorker() {
  const source = await findWorkerSource();
  await mkdir(publicDir, { recursive: true });
  await copyFile(source, destination);
  const { size } = await stat(destination);
  console.log(`Copied PDF.js worker from ${source} to ${destination} (${size} bytes).`);
}

copyWorker().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
