"""Tests slicing / constraints / export spritesheet."""
from __future__ import annotations

import shutil
import zipfile
from collections.abc import Iterator

import pytest


@pytest.fixture
def sprite_with_grid(test_input_image) -> Iterator[tuple[str, dict]]:
    """Installe la config slicing pour `test_small.png` → grille 2×2, cellules 16×16."""
    from server_fastapi.services import history_store

    stem = "test_small"
    grid = {
        "base": {
            "cols": 2, "rows": 2,
            "cellW": 16, "cellH": 16,
            "gapX": 0, "gapY": 0,
            "marginX": 0, "marginY": 0,
        },
        "overrides": [],
    }

    def _install(h: dict) -> None:
        h.setdefault(stem, {"source": f"inputs/{test_input_image}", "runs": []})
        h[stem]["slicing"] = grid

    history_store.update(_install)
    yield test_input_image, grid
    # cleanup via fixture test_input_image (purge complète)


def test_slicing_get_empty_returns_defaults(client, test_input_image):
    r = client.get(f"/api/slicing/{test_input_image}")
    assert r.status_code == 200
    body = r.json()
    assert body == {"base": None, "overrides": []}


def test_slicing_put_round_trip(client, test_input_image):
    r = client.put(
        f"/api/slicing/{test_input_image}",
        json={
            "base": {
                "cols": 4, "rows": 4, "cellW": 8, "cellH": 8,
                "gapX": 0, "gapY": 0, "marginX": 0, "marginY": 0,
            },
            "overrides": [],
        },
    )
    assert r.status_code == 200
    saved = r.json()
    assert saved["base"]["cols"] == 4
    assert saved["base"]["cellW"] == 8

    # Puis clear via PUT base=None
    r2 = client.put(f"/api/slicing/{test_input_image}", json={"base": None, "overrides": []})
    assert r2.status_code == 200
    assert r2.json() == {"base": None, "overrides": []}


def test_slicing_put_invalid_cols_rejected(client, test_input_image):
    r = client.put(
        f"/api/slicing/{test_input_image}",
        json={
            "base": {
                "cols": 999, "rows": 2, "cellW": 8, "cellH": 8,
                "gapX": 0, "gapY": 0, "marginX": 0, "marginY": 0,
            },
            "overrides": [],
        },
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["error"] == "invalid_config"
    assert any("cols" in e for e in detail["details"])


def test_slicing_bad_name_rejected(client):
    r = client.get("/api/slicing/../../etc/passwd")
    assert r.status_code in (400, 404)


def test_constraints_validate_empty_grid_returns_no_grid_warning(client, test_input_image):
    r = client.post(
        "/api/constraints/validate",
        json={"image": test_input_image, "constraints": {"pot": True}, "grid": {}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["violations"] == []
    assert body["warning"] == "no_grid"


def test_constraints_validate_detects_pot_violations(client, test_input_image):
    r = client.post(
        "/api/constraints/validate",
        json={
            "image": test_input_image,
            "constraints": {"pot": True},
            "grid": {
                "base": {"cols": 2, "rows": 2, "cellW": 7, "cellH": 7,
                         "gapX": 0, "gapY": 0, "marginX": 0, "marginY": 0},
                "overrides": [],
            },
        },
    )
    assert r.status_code == 200
    violations = r.json()["violations"]
    assert len(violations) == 4  # 2×2 cellules non-POT
    assert all(v["type"] == "pot" for v in violations)
    assert "padder à 8x8" in violations[0]["suggestion"]


def test_constraints_validate_detects_mul_n_violations(client, test_input_image):
    r = client.post(
        "/api/constraints/validate",
        json={
            "image": test_input_image,
            "constraints": {"mulN": 4},
            "grid": {
                "base": {"cols": 1, "rows": 1, "cellW": 7, "cellH": 7,
                         "gapX": 0, "gapY": 0, "marginX": 0, "marginY": 0},
                "overrides": [],
            },
        },
    )
    assert r.status_code == 200
    violations = r.json()["violations"]
    assert len(violations) == 1
    assert violations[0]["type"] == "mulN"


def test_constraints_bad_image_rejected(client):
    r = client.post(
        "/api/constraints/validate",
        json={"image": "../evil", "constraints": {}, "grid": {}},
    )
    assert r.status_code == 400


def test_export_zip_json_phaser_with_slicing(
    client, sprite_with_grid, tmp_path,
):
    image_name, _ = sprite_with_grid
    r = client.post(
        "/api/export",
        json={
            "image": image_name,
            "format": "json_phaser",
            "template": "{basename}_{col}_{row}",
            "options": {},
        },
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert int(r.headers["x-frames-count"]) == 4  # 2×2 = 4 frames

    # Le ZIP doit contenir atlas.png + atlas.json
    zpath = tmp_path / "export.zip"
    zpath.write_bytes(r.content)
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
        assert "atlas.png" in names
        assert "atlas.json" in names
        # JSON est valide et contient les 4 frames
        import json
        atlas = json.loads(zf.read("atlas.json"))
        assert len(atlas["frames"]) == 4


def test_export_individual_zips_each_frame(client, sprite_with_grid, tmp_path):
    image_name, _ = sprite_with_grid
    r = client.post(
        "/api/export",
        json={
            "image": image_name,
            "format": "individual",
            "template": "{basename}_{col}_{row}",
            "options": {},
        },
    )
    assert r.status_code == 200
    zpath = tmp_path / "export.zip"
    zpath.write_bytes(r.content)
    with zipfile.ZipFile(zpath) as zf:
        png_names = [n for n in zf.namelist() if n.endswith(".png")]
        assert len(png_names) == 4

    # Purge des artefacts export/ créés dans outputs/
    from server_fastapi.deps import OUTPUTS_DIR
    export_dir = OUTPUTS_DIR / "test_small" / "export"
    if export_dir.exists():
        shutil.rmtree(export_dir)


def test_export_fails_when_no_slicing(client, test_input_image):
    r = client.post(
        "/api/export",
        json={"image": test_input_image, "format": "json_phaser"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "no_slicing"


def test_export_fails_on_unknown_format(client, sprite_with_grid):
    image_name, _ = sprite_with_grid
    r = client.post(
        "/api/export",
        json={"image": image_name, "format": "alien_proto_9000"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "unknown_format"
