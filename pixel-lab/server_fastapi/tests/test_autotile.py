"""Tests /api/autotile/generate (Wang16 / Wang47 / Wang256)."""
from __future__ import annotations

import base64
import io
import shutil
from collections.abc import Iterator

import pytest
from PIL import Image


def _tile_data_url(color: tuple[int, int, int, int], size: int = 16) -> str:
    img = Image.new("RGBA", (size, size), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


@pytest.fixture
def clean_autotile_outputs() -> Iterator[None]:
    """Purge les dossiers `outputs/autotile_*` créés par les tests, et nettoie history."""
    from server_fastapi.deps import OUTPUTS_DIR
    from server_fastapi.services import history_store

    before = {p.name for p in OUTPUTS_DIR.glob("autotile_*") if p.is_dir()}
    yield
    # Purge des dossiers neufs
    for p in OUTPUTS_DIR.glob("autotile_*"):
        if p.is_dir() and p.name not in before:
            shutil.rmtree(p, ignore_errors=True)
            history_store.update(lambda h, name=p.name: h.pop(name, None))


def test_autotile_wang16_generates_atlas(client, clean_autotile_outputs):
    r = client.post(
        "/api/autotile/generate",
        json={
            "mode": "wang16",
            "tile_size": 16,
            "tiles": {
                "base": _tile_data_url((50, 50, 200, 255)),
                "edge": _tile_data_url((200, 50, 50, 255)),
            },
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gridLayout"]["cols"] == 4
    assert body["gridLayout"]["rows"] == 4
    assert body["gridLayout"]["mode"] == "wang16"
    assert body["iter"].startswith("outputs/autotile_")
    assert body["iter"].endswith("_autotile_wang16.png")


def test_autotile_bad_tile_size_rejected(client):
    r = client.post(
        "/api/autotile/generate",
        json={"mode": "wang16", "tile_size": 17, "tiles": {}},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "bad_tile_size"


def test_autotile_unknown_mode_rejected(client):
    r = client.post(
        "/api/autotile/generate",
        json={"mode": "wang999", "tile_size": 16, "tiles": {}},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "unknown_mode"


def test_autotile_missing_base_tile_rejected(client):
    r = client.post(
        "/api/autotile/generate",
        json={
            "mode": "wang16",
            "tile_size": 16,
            "tiles": {"edge": _tile_data_url((0, 0, 0, 255))},
        },
    )
    assert r.status_code == 400
    assert "missing_tile_base" in r.json()["detail"]


def test_autotile_bad_data_url_rejected(client):
    r = client.post(
        "/api/autotile/generate",
        json={
            "mode": "wang16",
            "tile_size": 16,
            "tiles": {"base": "not_a_data_url", "edge": _tile_data_url((0, 0, 0, 255))},
        },
    )
    assert r.status_code == 400
    assert "bad_tile_base" in r.json()["detail"]
