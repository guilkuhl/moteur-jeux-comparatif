"""Routers inputs / outputs / bgmask + history_store."""
from __future__ import annotations

import io
import shutil
from pathlib import Path

import pytest
from PIL import Image


def _png_bytes(size: tuple[int, int] = (8, 8)) -> bytes:
    img = Image.new("RGBA", size, (12, 34, 56, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_list_inputs_returns_json_array(client):
    r = client.get("/api/inputs")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    for f in body:
        assert "name" in f and "processed" in f


def test_upload_and_delete_input_roundtrip(client):
    """Upload d'un PNG, vérif présence, delete puis absence."""
    from server_fastapi.deps import INPUTS_DIR, INPUTS_TRASH

    name = "pytest_upload_sample.png"
    target = INPUTS_DIR / name
    # Cleanup préalable si un test précédent a crashé
    target.unlink(missing_ok=True)

    r = client.post(
        "/api/inputs",
        files={"file": (name, _png_bytes(), "image/png")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["basename"] == name
    assert target.exists()

    r2 = client.delete(f"/api/inputs/{name}")
    assert r2.status_code == 200
    assert not target.exists()

    # Le trash doit contenir l'archive
    trashed = list(INPUTS_TRASH.glob(f"{Path(name).stem}_*{Path(name).suffix}"))
    assert trashed, "l'image supprimée doit être dans inputs/_trash/"
    for t in trashed:
        t.unlink()  # cleanup du trash pour éviter la pollution


def test_upload_rejects_unsupported_extension(client):
    r = client.post(
        "/api/inputs",
        files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
    )
    assert r.status_code == 415


def test_delete_nonexistent_input_returns_404(client):
    r = client.delete("/api/inputs/absolutely_not_there_xyz.png")
    assert r.status_code == 404


def test_bgmask_happy_path(client, test_input_image):
    r = client.get(f"/api/bgmask?image={test_input_image}&tolerance=8")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.headers.get("x-cache") in ("HIT", "MISS")
    # 2e appel → cache HIT
    r2 = client.get(f"/api/bgmask?image={test_input_image}&tolerance=8")
    assert r2.status_code == 200
    assert r2.headers.get("x-cache") == "HIT"


def test_bgmask_tolerance_out_of_range_rejected(client):
    r = client.get("/api/bgmask?image=whatever.png&tolerance=999")
    assert r.status_code == 422


def test_history_store_update_atomic(tmp_path, monkeypatch):
    """Le mutator reçoit un dict mutable et la sauvegarde écrit le JSON final."""
    import server_fastapi.services.history_store as hs

    hist_file = tmp_path / "history.json"
    monkeypatch.setattr(hs, "HISTORY_FILE", hist_file)

    hs.update(lambda h: h.update({"foo": {"source": "x", "runs": []}}))
    assert hist_file.exists()
    data = hs.load()
    assert "foo" in data

    hs.update(lambda h: h.pop("foo", None))
    assert "foo" not in hs.load()


@pytest.fixture
def output_stem_with_iter() -> str:
    """Prépare `outputs/<stem>/iter_001_fake.png` pour tester DELETE /api/outputs."""
    from server_fastapi.deps import OUTPUTS_DIR
    stem = "pytest_out_delete_xyz"
    d = OUTPUTS_DIR / stem
    d.mkdir(parents=True, exist_ok=True)
    f = d / "iter_001_fake.png"
    f.write_bytes(_png_bytes())
    try:
        yield stem
    finally:
        if d.exists():
            shutil.rmtree(d)


def test_delete_one_output(client, output_stem_with_iter):
    from server_fastapi.deps import OUTPUTS_DIR
    stem = output_stem_with_iter
    r = client.delete(f"/api/outputs/{stem}/iter_001_fake.png")
    assert r.status_code == 200
    assert not (OUTPUTS_DIR / stem / "iter_001_fake.png").exists()


def test_delete_all_outputs(client, output_stem_with_iter):
    from server_fastapi.deps import OUTPUTS_DIR
    stem = output_stem_with_iter
    r = client.delete(f"/api/outputs/{stem}")
    assert r.status_code == 200
    assert not list((OUTPUTS_DIR / stem).glob("iter_*"))


def test_delete_one_output_bad_name_400(client):
    r = client.delete("/api/outputs/..evil../iter_001.png")
    assert r.status_code == 400
