from __future__ import annotations

from fastapi.testclient import TestClient

from tests.pdf_factory import make_overlap_pdf_bytes


def _center(bbox: list[float]) -> tuple[float, float]:
    x0, y0, x1, y1 = bbox
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _intersection_area(a: list[float], b: list[float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    x_left = max(ax0, bx0)
    y_top = max(ay0, by0)
    x_right = min(ax1, bx1)
    y_bottom = min(ay1, by1)
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0
    return (x_right - x_left) * (y_bottom - y_top)


def test_hittest_point_and_rect(client: TestClient) -> None:
    pdf_bytes = make_overlap_pdf_bytes()
    files = {"file": ("overlap.pdf", pdf_bytes, "application/pdf")}
    response = client.post("/v1/documents/upload", files=files)
    assert response.status_code == 200
    doc_id = response.json()["document"]["doc_id"]

    ir_response = client.get(f"/v1/ir/{doc_id}?page=0")
    assert ir_response.status_code == 200
    primitives = ir_response.json()["primitives"]

    path_primitives = [primitive for primitive in primitives if primitive["kind"] == "path"]
    assert len(path_primitives) == 2

    expected_a_center = (150.0, 150.0)
    expected_b_center = (200.0, 200.0)
    primitive_a = min(path_primitives, key=lambda item: _distance(_center(item["bbox"]), expected_a_center))
    primitive_b = min(path_primitives, key=lambda item: _distance(_center(item["bbox"]), expected_b_center))

    point_response = client.post(
        f"/v1/hittest/{doc_id}?page=0",
        json={"point": {"x": 160.0, "y": 160.0}},
    )
    assert point_response.status_code == 200
    point_candidates = point_response.json()["candidates"]
    assert point_candidates[0]["id"] == primitive_a["id"]

    selection_rect = {"x0": 140.0, "y0": 140.0, "x1": 230.0, "y1": 230.0}
    rect_response = client.post(
        f"/v1/hittest/{doc_id}?page=0",
        json={"rect": selection_rect},
    )
    assert rect_response.status_code == 200
    rect_candidates = rect_response.json()["candidates"]
    area_a = _intersection_area([selection_rect["x0"], selection_rect["y0"], selection_rect["x1"], selection_rect["y1"]], primitive_a["bbox"])
    area_b = _intersection_area([selection_rect["x0"], selection_rect["y0"], selection_rect["x1"], selection_rect["y1"]], primitive_b["bbox"])
    expected_first = primitive_a if area_a > area_b else primitive_b
    assert rect_candidates[0]["id"] == expected_first["id"]

    rect_second = client.post(
        f"/v1/hittest/{doc_id}?page=0",
        json={"rect": selection_rect},
    )
    assert rect_second.status_code == 200
    assert rect_candidates == rect_second.json()["candidates"]
