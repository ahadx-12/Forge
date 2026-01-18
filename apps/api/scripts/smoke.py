from __future__ import annotations

import json
import os
import sys

import fitz
import httpx


def _make_smoke_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=400, height=400)
    page.draw_rect(fitz.Rect(50, 50, 350, 200), color=(0.1, 0.3, 0.6), fill=(0.1, 0.3, 0.6))
    page.insert_text((70, 110), "Forge Smoke Test", fontsize=14, color=(1, 1, 1))
    page.insert_text((70, 140), "Edit target", fontsize=12, color=(1, 1, 1))
    payload = doc.tobytes()
    doc.close()
    return payload


def main() -> int:
    base_url = os.getenv("FORGE_SMOKE_API_BASE_URL", "http://localhost:8000").rstrip("/")
    client = httpx.Client(base_url=base_url, timeout=30)

    upload = client.post(
        "/v1/documents/upload",
        files={"file": ("smoke.pdf", _make_smoke_pdf(), "application/pdf")},
    )
    upload.raise_for_status()
    doc_id = upload.json()["document"]["doc_id"]

    ir = client.get(f"/v1/ir/{doc_id}", params={"page": 0})
    ir.raise_for_status()
    primitives = ir.json()["primitives"]
    text_target = next(item for item in primitives if item["kind"] == "text")

    bbox = text_target["bbox"]
    hit = client.post(
        f"/v1/hittest/{doc_id}",
        params={"page": 0},
        json={"point": {"x": (bbox[0] + bbox[2]) / 2, "y": (bbox[1] + bbox[3]) / 2}},
    )
    hit.raise_for_status()

    patch_payload = {
        "doc_id": doc_id,
        "patchset": {
            "ops": [
                {
                    "op": "replace_text",
                    "target_id": text_target["id"],
                    "new_text": "Smoke OK",
                    "policy": "FIT_IN_BOX",
                }
            ],
            "page_index": 0,
            "selected_ids": [text_target["id"]],
            "rationale_short": "Smoke test edit",
        },
    }
    commit = client.post("/v1/patch/commit", json=patch_payload)
    commit.raise_for_status()

    composite = client.get(f"/v1/composite/ir/{doc_id}", params={"page": 0})
    composite.raise_for_status()

    export = client.post(f"/v1/export/{doc_id}", params={"mask_mode": "AUTO_BG"})
    export.raise_for_status()
    if not export.content.startswith(b"%PDF"):
        raise RuntimeError("Export did not return PDF bytes")

    print(json.dumps({"status": "ok", "doc_id": doc_id}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
