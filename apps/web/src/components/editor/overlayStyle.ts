import type { ForgeOverlayPatchOp } from "@/lib/api";

type StyleFields = {
  color?: string | null;
  stroke_color?: string | null;
  stroke_width_pt?: number | null;
  fill_color?: string | null;
};

export function buildUpdateStyleOp(
  elementId: string,
  kind: "text_run" | "path",
  style: StyleFields
): ForgeOverlayPatchOp | null {
  const filtered = Object.fromEntries(
    Object.entries(style).filter(([, value]) => value !== undefined && value !== null)
  );
  if (!Object.keys(filtered).length) {
    return null;
  }
  return {
    type: "update_style",
    element_id: elementId,
    kind,
    style: filtered
  };
}
