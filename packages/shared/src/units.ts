export function formatBytes(bytes: number): string {
  if (Number.isNaN(bytes) || bytes <= 0) {
    return "0 KB";
  }
  const kb = bytes / 1024;
  if (kb < 1024) {
    return `${kb.toFixed(1)} KB`;
  }
  return `${(kb / 1024).toFixed(1)} MB`;
}
