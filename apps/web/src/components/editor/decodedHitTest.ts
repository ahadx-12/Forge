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

const DEFAULT_KINDS = ["text_run"];

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
