export type BBox = [number, number, number, number];

export type PixelRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

export type OverlayGeometryContext = {
  containerWidth: number;
  containerHeight: number;
  pageWidthPt?: number;
  pageHeightPt?: number;
  imageWidthPx?: number;
  imageHeightPx?: number;
};

type BBoxSpace = "normalized" | "points" | "pixels";

type SpaceScale = {
  scaleX: number;
  scaleY: number;
  flipMax: number;
};

const getSpaceScale = (space: BBoxSpace, context: OverlayGeometryContext): SpaceScale => {
  if (space === "normalized") {
    return {
      scaleX: context.containerWidth,
      scaleY: context.containerHeight,
      flipMax: 1
    };
  }

  if (space === "points") {
    const widthPt = context.pageWidthPt ?? context.containerWidth;
    const heightPt = context.pageHeightPt ?? context.containerHeight;
    return {
      scaleX: context.containerWidth / widthPt,
      scaleY: context.containerHeight / heightPt,
      flipMax: heightPt
    };
  }

  const widthPx = context.imageWidthPx ?? context.containerWidth;
  const heightPx = context.imageHeightPx ?? context.containerHeight;
  return {
    scaleX: context.containerWidth / widthPx,
    scaleY: context.containerHeight / heightPx,
    flipMax: heightPx
  };
};

const computeRect = (bbox: BBox, scale: SpaceScale, shouldFlipY: boolean): PixelRect => {
  const [x0, y0, x1, y1] = bbox;
  const left = x0 * scale.scaleX;
  const top = shouldFlipY ? (scale.flipMax - y1) * scale.scaleY : y0 * scale.scaleY;
  const width = Math.max(0, (x1 - x0) * scale.scaleX);
  const height = Math.max(0, (y1 - y0) * scale.scaleY);

  return {
    left,
    top,
    width,
    height
  };
};

const detectSpaceFromBboxes = (bboxes: BBox[], context: OverlayGeometryContext): BBoxSpace => {
  const maxX = Math.max(...bboxes.map((bbox) => bbox[2]), 0);
  const maxY = Math.max(...bboxes.map((bbox) => bbox[3]), 0);

  if (maxX <= 1.5 && maxY <= 1.5) {
    return "normalized";
  }

  if (
    context.pageWidthPt &&
    context.pageHeightPt &&
    maxX <= context.pageWidthPt * 1.5 &&
    maxY <= context.pageHeightPt * 1.5
  ) {
    return "points";
  }

  if (
    context.imageWidthPx &&
    context.imageHeightPx &&
    maxX <= context.imageWidthPx * 1.5 &&
    maxY <= context.imageHeightPx * 1.5
  ) {
    return "pixels";
  }

  return "normalized";
};

const computeAverageCenter = (bboxes: BBox[], spaceHeight: number): number => {
  if (!bboxes.length || spaceHeight <= 0) {
    return 0.5;
  }

  const total = bboxes.reduce((sum, bbox) => sum + (bbox[1] + bbox[3]) / 2, 0);
  return total / bboxes.length / spaceHeight;
};

const resolveSpaceHeight = (space: BBoxSpace, context: OverlayGeometryContext): number => {
  if (space === "normalized") {
    return 1;
  }
  if (space === "points") {
    return context.pageHeightPt ?? 1;
  }
  return context.imageHeightPx ?? 1;
};

export const createBBoxConverter = (
  bboxes: BBox[],
  context: OverlayGeometryContext
): {
  space: BBoxSpace;
  shouldFlipY: boolean;
  toPixelRect: (bbox: BBox) => PixelRect;
} => {
  const space = detectSpaceFromBboxes(bboxes, context);
  const spaceHeight = resolveSpaceHeight(space, context);
  const averageCenter = computeAverageCenter(bboxes, spaceHeight);
  const shouldFlipY = averageCenter > 0.55;
  const scale = getSpaceScale(space, context);

  return {
    space,
    shouldFlipY,
    toPixelRect: (bbox) => computeRect(bbox, scale, shouldFlipY)
  };
};
