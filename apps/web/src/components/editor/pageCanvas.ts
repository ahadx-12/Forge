export type PageCanvasSize = {
  width: number;
  height: number;
};

export type PagePixelRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

const MIN_PAGE_WIDTH = 320;
const MAX_PAGE_WIDTH = 900;
const DEFAULT_PADDING = 32;

export const getPageCanvasSize = (
  containerWidth: number,
  pageWidthPt: number,
  pageHeightPt: number,
  padding: number = DEFAULT_PADDING
): PageCanvasSize => {
  if (containerWidth <= 0 || pageWidthPt <= 0 || pageHeightPt <= 0) {
    return { width: 0, height: 0 };
  }

  const availableWidth = Math.max(containerWidth - padding, MIN_PAGE_WIDTH);
  const width = Math.max(MIN_PAGE_WIDTH, Math.min(MAX_PAGE_WIDTH, availableWidth));
  const height = width * (pageHeightPt / pageWidthPt);

  return { width, height };
};

export const normalizedToPixelRect = (
  bbox: [number, number, number, number],
  pageSize: PageCanvasSize
): PagePixelRect => {
  const [x0, y0, x1, y1] = bbox;
  const left = x0 * pageSize.width;
  const top = y0 * pageSize.height;
  const width = Math.max(0, (x1 - x0) * pageSize.width);
  const height = Math.max(0, (y1 - y0) * pageSize.height);

  return { left, top, width, height };
};
