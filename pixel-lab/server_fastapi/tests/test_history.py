"""Tests /api/history/prune — retire entrées orphelines de history.json."""
from __future__ import annotations

import shutil

import pytest


@pytest.fixture
def orphan_history_entry():
    """Pose dans history.json une entrée dont le fichier source n'existe pas dans inputs/,
    et place un outputs/<stem>/ correspondant à archiver."""
    from server_fastapi.deps import INPUTS_DIR, INPUTS_TRASH, OUTPUTS_DIR, OUTPUTS_TRASH
    from server_fastapi.services import history_store

    stem = "pytest_orphan_xyz"
    out_dir = OUTPUTS_DIR / stem
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "iter_001_fake.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    def _install(h: dict) -> None:
        h[stem] = {"source": f"inputs/{stem}.png", "runs": [
            {"algo": "sharpen", "method": "unsharp_mask", "params": {}, "output": f"outputs/{stem}/iter_001_fake.png"}
        ]}

    history_store.update(_install)
    # Pas de fichier réel dans inputs/ → stem est bien « orphelin »
    assert not (INPUTS_DIR / f"{stem}.png").exists()
    try:
        yield stem
    finally:
        # Nettoyage du trash et de l'éventuel résidu
        for trash in (INPUTS_TRASH, OUTPUTS_TRASH):
            for p in trash.glob(f"{stem}*"):
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    p.unlink(missing_ok=True)
        if out_dir.exists():
            shutil.rmtree(out_dir)
        history_store.update(lambda h: h.pop(stem, None))


def test_prune_archives_orphan_entry(client, orphan_history_entry):
    stem = orphan_history_entry
    r = client.post(
        "/api/history/prune",
        json={"basenames": [f"{stem}.png"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert stem in body["pruned"]
    # L'entrée est retirée
    from server_fastapi.services import history_store
    assert stem not in history_store.load()


def test_prune_skips_entries_with_existing_source(client, test_input_image):
    """Si le fichier source existe encore dans inputs/, l'entrée est préservée."""
    from server_fastapi.services import history_store

    stem = "test_small"
    # Pose une entrée dans history pointant sur test_input_image (qui existe)
    history_store.update(lambda h: h.setdefault(stem, {"source": f"inputs/{test_input_image}", "runs": []}))

    r = client.post("/api/history/prune", json={"basenames": [test_input_image]})
    assert r.status_code == 200
    body = r.json()
    assert stem not in body["pruned"]
    assert any(s["reason"] == "source file still present" for s in body["skipped"])


def test_prune_skips_unknown_entries(client):
    r = client.post(
        "/api/history/prune",
        json={"basenames": ["totally_unknown_xyz.png"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["pruned"] == []
    assert body["skipped"][0]["reason"] == "not_in_history"


def test_prune_rejects_bad_name(client):
    r = client.post(
        "/api/history/prune",
        json={"basenames": ["../../etc/passwd"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["skipped"][0]["reason"] == "bad_name"


def test_prune_requires_list_payload(client):
    r = client.post(
        "/api/history/prune",
        json={"basenames": "not-a-list"},
    )
    assert r.status_code == 400
