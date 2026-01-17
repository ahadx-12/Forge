export function shortId(input: string): string {
  if (!input) {
    return "";
  }
  return input.replace(/-/g, "").slice(0, 8);
}
