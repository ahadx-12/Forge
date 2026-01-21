export type PdfJsRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value));

export const roundTo = (value: number, decimals = 2) =>
  Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals);

export function normalizeBbox(
  rect: PdfJsRect,
  viewportWidth: number,
  viewportHeight: number
): [number, number, number, number] {
  if (!viewportWidth || !viewportHeight) {
    return [0, 0, 0, 0];
  }
  const left = clamp(rect.left / viewportWidth);
  const top = clamp(rect.top / viewportHeight);
  const right = clamp((rect.left + rect.width) / viewportWidth);
  const bottom = clamp((rect.top + rect.height) / viewportHeight);
  return [left, top, right, bottom];
}

export function hashString(value: string): string {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16);
}

export function buildElementId(pageIndex: number, rect: PdfJsRect, text: string): string {
  const signature = [
    pageIndex,
    roundTo(rect.left),
    roundTo(rect.top),
    roundTo(rect.width),
    roundTo(rect.height),
    text
  ].join("|");
  return `p${pageIndex}_${hashString(signature)}`;
}
