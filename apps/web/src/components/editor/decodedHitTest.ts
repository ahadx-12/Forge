export type BBox = [number, number, number, number];

export type DecodedElementLike = {
  id: string;
  kind: string;
  bbox_norm: BBox;
};

export type PickOptions = {
  kinds?: string[];
  maxResults?: number;
};

export type TextPickFallbackOptions = {
  maxResults?: number;
  paddingPx?: number;
  nearestDistancePx?: number;
  viewportSize?: { width: number; height: number };
  includePathsWhenEmpty?: boolean;
};

const DEFAULT_KINDS = ["text_run", "path"];
const TEXT_KINDS = ["text_run"];

const DEFAULT_PADDING_PX = 8;
const DEFAULT_NEAREST_DISTANCE_PX = 24;

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function clampBBox(bbox: BBox): BBox {
  const [x0, y0, x1, y1] = bbox;
  const xMin = Math.max(0, Math.min(1, Math.min(x0, x1)));
  const xMax = Math.max(0, Math.min(1, Math.max(x0, x1)));
  const yMin = Math.max(0, Math.min(1, Math.min(y0, y1)));
  const yMax = Math.max(0, Math.min(1, Math.max(y0, y1)));
  return [xMin, yMin, xMax, yMax];
}

export function area(bbox: BBox): number {
  const [x0, y0, x1, y1] = bbox;
  return Math.max(0, x1 - x0) * Math.max(0, y1 - y0);
}

export function intersectArea(a: BBox, b: BBox): number {
  const [ax0, ay0, ax1, ay1] = a;
  const [bx0, by0, bx1, by1] = b;
  const ix0 = Math.max(ax0, bx0);
  const iy0 = Math.max(ay0, by0);
  const ix1 = Math.min(ax1, bx1);
  const iy1 = Math.min(ay1, by1);
  return Math.max(0, ix1 - ix0) * Math.max(0, iy1 - iy0);
}

function containsBBox(region: BBox, target: BBox): boolean {
  const [rx0, ry0, rx1, ry1] = region;
  const [tx0, ty0, tx1, ty1] = target;
  return rx0 <= tx0 && ry0 <= ty0 && rx1 >= tx1 && ry1 >= ty1;
}

function expandBBox(region: BBox, paddingX: number, paddingY: number): BBox {
  const [x0, y0, x1, y1] = clampBBox(region);
  return [
    clamp(x0 - paddingX, 0, 1),
    clamp(y0 - paddingY, 0, 1),
    clamp(x1 + paddingX, 0, 1),
    clamp(y1 + paddingY, 0, 1)
  ];
}

function bboxCenter(bbox: BBox): { x: number; y: number } {
  const [x0, y0, x1, y1] = bbox;
  return { x: (x0 + x1) / 2, y: (y0 + y1) / 2 };
}

function distancePx(
  a: { x: number; y: number },
  b: { x: number; y: number },
  viewportSize: { width: number; height: number }
): number {
  const dx = (a.x - b.x) * viewportSize.width;
  const dy = (a.y - b.y) * viewportSize.height;
  return Math.hypot(dx, dy);
}

export function pickDecodedElementsInRegion<T extends DecodedElementLike>(
  elements: T[],
  region: BBox,
  options: PickOptions = {}
): T[] {
  const kinds = options.kinds ?? DEFAULT_KINDS;
  const maxResults = options.maxResults ?? 20;
  const clampedRegion = clampBBox(region);

  const scored = elements
    .filter((element) => kinds.includes(element.kind))
    .map((element) => {
      const bbox = clampBBox(element.bbox_norm);
      const elementArea = area(bbox);
      if (elementArea <= 0) {
        return null;
      }
      const overlap = intersectArea(clampedRegion, bbox);
      const overlapRatio = overlap / elementArea;
      if (overlapRatio < 0.1 && !containsBBox(clampedRegion, bbox)) {
        return null;
      }
      return { element, overlapRatio, elementArea };
    })
    .filter(Boolean) as { element: T; overlapRatio: number; elementArea: number }[];

  scored.sort((a, b) => {
    if (b.overlapRatio !== a.overlapRatio) {
      return b.overlapRatio - a.overlapRatio;
    }
    if (a.elementArea !== b.elementArea) {
      return a.elementArea - b.elementArea;
    }
    return a.element.id.localeCompare(b.element.id);
  });

  return scored.slice(0, maxResults).map((item) => item.element);
}

export function pickDecodedTextElementsWithFallback<T extends DecodedElementLike>(
  elements: T[],
  region: BBox,
  options: TextPickFallbackOptions = {}
): T[] {
  const maxResults = options.maxResults ?? 20;
  const viewportSize = options.viewportSize ?? { width: 1, height: 1 };
  const paddingPx = options.paddingPx ?? DEFAULT_PADDING_PX;
  const nearestDistancePx = options.nearestDistancePx ?? DEFAULT_NEAREST_DISTANCE_PX;
  const includePathsWhenEmpty = options.includePathsWhenEmpty ?? true;

  const textElements = elements.filter((element) => TEXT_KINDS.includes(element.kind));
  const clampedRegion = clampBBox(region);

  const primary = pickDecodedElementsInRegion(textElements, clampedRegion, {
    kinds: TEXT_KINDS,
    maxResults
  });
  if (primary.length) {
    return primary;
  }

  if (paddingPx > 0) {
    const paddingX = paddingPx / Math.max(1, viewportSize.width);
    const paddingY = paddingPx / Math.max(1, viewportSize.height);
    const expanded = expandBBox(clampedRegion, paddingX, paddingY);
    const expandedPicked = pickDecodedElementsInRegion(textElements, expanded, {
      kinds: TEXT_KINDS,
      maxResults
    });
    if (expandedPicked.length) {
      return expandedPicked;
    }
  }

  if (nearestDistancePx > 0 && textElements.length) {
    const regionCenter = bboxCenter(clampedRegion);
    let best: { element: T; distance: number } | null = null;
    for (const element of textElements) {
      const center = bboxCenter(clampBBox(element.bbox_norm));
      const distance = distancePx(regionCenter, center, viewportSize);
      if (!best || distance < best.distance) {
        best = { element, distance };
      }
    }
    if (best && best.distance <= nearestDistancePx) {
      return [best.element];
    }
  }

  if (includePathsWhenEmpty) {
    return pickDecodedElementsInRegion(elements, clampedRegion, { maxResults });
  }

  return [];
}
