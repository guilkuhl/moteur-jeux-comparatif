"""Tests pour /api/presets — CRUD de pipelines nommés."""
from __future__ import annotations

from collections.abc import Iterator

import pytest

from server_fastapi.deps import PRESETS_FILE


@pytest.fixture(autouse=True)
def isolate_presets_file() -> Iterator[None]:
    """Sauvegarde / restaure presets.json autour de chaque test — évite de
    polluer le fichier utilisateur tout en validant la persistance réelle."""
    backup = None
    if PRESETS_FILE.exists():
        backup = PRESETS_FILE.read_bytes()
    PRESETS_FILE.unlink(missing_ok=True)
    yield
    PRESETS_FILE.unlink(missing_ok=True)
    if backup is not None:
        PRESETS_FILE.write_bytes(backup)


def test_list_empty_by_default(client):
    res = client.get("/api/presets")
    assert res.status_code == 200
    assert res.json() == []


def test_create_then_list(client):
    body = {
        "name": "retro_8bit",
        "pipeline": [
            {"algo": "sharpen", "method": "unsharp_mask", "params": {"radius": 1.2}},
        ],
    }
    res = client.post("/api/presets", json=body)
    assert res.status_code == 201
    created = res.json()
    assert created["name"] == "retro_8bit"
    assert "updated_at" in created

    listing = client.get("/api/presets").json()
    assert len(listing) == 1
    assert listing[0]["name"] == "retro_8bit"


def test_upsert_overwrites(client):
    body = {
        "name": "p1",
        "pipeline": [{"algo": "sharpen", "method": "unsharp_mask", "params": {}}],
    }
    client.post("/api/presets", json=body)
    body["pipeline"] = [{"algo": "denoise", "method": "median", "params": {}}]
    res = client.post("/api/presets", json=body)
    assert res.status_code == 201
    listing = client.get("/api/presets").json()
    assert len(listing) == 1
    assert listing[0]["pipeline"][0]["algo"] == "denoise"


def test_delete_roundtrip(client):
    body = {
        "name": "to_delete",
        "pipeline": [{"algo": "sharpen", "method": "unsharp_mask", "params": {}}],
    }
    client.post("/api/presets", json=body)
    res = client.delete("/api/presets/to_delete")
    assert res.status_code == 204
    assert client.get("/api/presets").json() == []


def test_delete_unknown_returns_404(client):
    assert client.delete("/api/presets/ghost").status_code == 404


def test_invalid_name_rejected(client):
    body = {
        "name": "has spaces",
        "pipeline": [{"algo": "sharpen", "method": "unsharp_mask", "params": {}}],
    }
    res = client.post("/api/presets", json=body)
    assert res.status_code == 422


def test_invalid_pipeline_rejected(client):
    body = {
        "name": "bad",
        "pipeline": [{"algo": "sharpen", "method": "does_not_exist", "params": {}}],
    }
    res = client.post("/api/presets", json=body)
    assert res.status_code == 422
