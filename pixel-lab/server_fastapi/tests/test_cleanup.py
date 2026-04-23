"""Tests /api/cleanup/{detect-duplicates,detect-subpixel,normalize,report}."""
from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture
def grid_2x2(test_input_image) -> Iterator[str]:
    """Installe un slicing 2×2 (16×16) sur `test_small.png`."""
    from server_fastapi.services import history_store

    stem = "test_small"

    def _install(h: dict) -> None:
        h.setdefault(stem, {"source": f"inputs/{test_input_image}", "runs": []})
        h[stem]["slicing"] = {
            "base": {"cols": 2, "rows": 2, "cellW": 16, "cellH": 16,
                     "gapX": 0, "gapY": 0, "marginX": 0, "marginY": 0},
            "overrides": [],
        }

    history_store.update(_install)
    yield test_input_image
    # le cleanup de test_input_image purge outputs/test_small/ et l'entrée history


def test_detect_duplicates_returns_pairs(client, grid_2x2):
    r = client.post(
        "/api/cleanup/detect-duplicates",
        json={"image": grid_2x2, "similarity_threshold": 20},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["threshold"] == 20
    assert isinstance(body["pairs"], list)


def test_detect_duplicates_fails_without_slicing(client, test_input_image):
    r = client.post(
        "/api/cleanup/detect-duplicates",
        json={"image": test_input_image},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "no_slicing"


def test_detect_subpixel_runs(client, grid_2x2):
    r = client.post(
        "/api/cleanup/detect-subpixel",
        json={"image": grid_2x2},
    )
    assert r.status_code == 200
    body = r.json()
    assert "shifts" in body
    assert isinstance(body["shifts"], list)


def test_detect_subpixel_fails_without_slicing(client, test_input_image):
    r = client.post(
        "/api/cleanup/detect-subpixel",
        json={"image": test_input_image},
    )
    assert r.status_code == 400


def test_normalize_produces_iter_png(client, grid_2x2):
    from server_fastapi.deps import OUTPUTS_DIR

    r = client.post(
        "/api/cleanup/normalize",
        json={"image": grid_2x2, "alignment": "center"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["iter"].startswith("outputs/test_small/iter_")
    assert body["iter"].endswith("_normalize.png")
    assert len(body["dimensions"]) == 2
    assert len(body["cellSize"]) == 2
    # Le fichier existe vraiment sur disque
    rel = body["iter"].removeprefix("outputs/")
    assert (OUTPUTS_DIR / rel).exists()


def test_report_returns_json_with_disposition(client, grid_2x2):
    r = client.get(f"/api/cleanup/report?image={grid_2x2}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert "attachment" in r.headers["content-disposition"]
    body = r.json()
    assert "duplicates" in body
    assert "size_variants" in body
    assert body["frame_count"] == 4


def test_report_bad_image_rejected(client):
    r = client.get("/api/cleanup/report?image=../evil")
    assert r.status_code == 400


def test_cleanup_endpoints_reject_bad_image(client):
    for endpoint in ("detect-duplicates", "detect-subpixel", "normalize"):
        r = client.post(f"/api/cleanup/{endpoint}", json={"image": "../evil"})
        assert r.status_code == 400, f"{endpoint} should reject path traversal"
