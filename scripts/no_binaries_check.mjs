import { execSync } from "node:child_process";
import path from "node:path";

const forbiddenExtensions = new Set([
  ".pdf",
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".bmp",
  ".tiff",
  ".ico",
  ".zip",
  ".gz",
  ".tar",
  ".rar",
  ".7z",
  ".woff",
  ".woff2",
  ".ttf",
  ".otf",
  ".eot",
  ".mp4",
  ".mov",
  ".avi",
  ".mp3",
  ".wav"
]);

const output = execSync("git ls-files -z", { encoding: "utf8" });
const files = output.split("\u0000").filter(Boolean);
const violations = files.filter((file) => forbiddenExtensions.has(path.extname(file).toLowerCase()));

if (violations.length > 0) {
  console.error("Binary files detected:");
  for (const file of violations) {
    console.error(`- ${file}`);
  }
  process.exit(1);
}

console.log("No binary files detected.");
