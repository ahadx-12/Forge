export type OverlayScaleInput = {
  naturalWidth: number;
  naturalHeight: number;
  clientWidth: number;
  clientHeight: number;
};

export function computeOverlayScale({
  naturalWidth,
  naturalHeight,
  clientWidth,
  clientHeight
}: OverlayScaleInput): { scaleX: number; scaleY: number } {
  if (naturalWidth <= 0 || naturalHeight <= 0) {
    return { scaleX: 1, scaleY: 1 };
  }
  if (clientWidth <= 0 || clientHeight <= 0) {
    return { scaleX: 1, scaleY: 1 };
  }
  return {
    scaleX: clientWidth / naturalWidth,
    scaleY: clientHeight / naturalHeight
  };
}
