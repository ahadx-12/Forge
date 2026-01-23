import assert from "node:assert/strict";
import { test } from "node:test";

import { buildUpdateStyleOp } from "./overlayStyle";

test("buildUpdateStyleOp returns null when no fields", () => {
  const op = buildUpdateStyleOp("element-1", "path", {});
  assert.equal(op, null);
});

test("buildUpdateStyleOp builds update_style payload", () => {
  const op = buildUpdateStyleOp("element-1", "path", {
    stroke_color: "#ff0000",
    stroke_width_pt: 2
  });
  assert.deepEqual(op, {
    type: "update_style",
    element_id: "element-1",
    kind: "path",
    style: {
      stroke_color: "#ff0000",
      stroke_width_pt: 2
    }
  });
});
