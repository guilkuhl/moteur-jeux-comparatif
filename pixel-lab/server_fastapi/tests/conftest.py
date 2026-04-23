"""Fixtures pytest partagées."""
from __future__ import annotations

import shutil
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client() -> TestClient:
    """TestClient FastAPI — routage complet, middlewares actifs."""
    from server_fastapi.main import app
    return TestClient(app)


@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    """Génère un petit PNG 8x8 déterministe dans `tmp_path`."""
    img = Image.new("RGBA", (8, 8), (100, 150, 200, 255))
    p = tmp_path / "sample.png"
    img.save(p)
    return p


@pytest.fixture
def test_input_image() -> Iterator[str]:
    """Copie la fixture `test_small.png` dans `pixel-lab/inputs/` le temps d'un test,
    puis nettoie **toutes** les side-effects :
    - fichier d'input copié → supprimé,
    - dossier `outputs/test_small/` créé par les jobs → supprimé,
    - entrée `test_small` dans `history.json` → retirée.

    Tests qui touchent au FS doivent être parfaitement idempotents ; sans ce
    cleanup exhaustif, les artefacts polluent le repo utilisateur.
    """
    from server_fastapi.deps import INPUTS_DIR, OUTPUTS_DIR
    from server_fastapi.services import history_store

    name = "test_small.png"
    stem = "test_small"
    src = FIXTURES / "inputs" / name
    dest = INPUTS_DIR / name

    backup = None
    if dest.exists():
        backup = dest.with_suffix(".png.bak-pytest")
        shutil.move(str(dest), str(backup))
    shutil.copy2(src, dest)
    try:
        yield name
    finally:
        dest.unlink(missing_ok=True)
        out_dir = OUTPUTS_DIR / stem
        if out_dir.exists():
            # Un thread worker peut encore écrire dans out_dir après la fin du test.
            # On attend jusqu'à 5 s que le job se termine avant de supprimer.
            deadline = time.time() + 5.0
            while time.time() < deadline:
                try:
                    shutil.rmtree(out_dir)
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                shutil.rmtree(out_dir, ignore_errors=True)
        history_store.update(lambda h: h.pop(stem, None))
        if backup is not None:
            shutil.move(str(backup), str(dest))


@pytest.fixture
def reset_preview_cache() -> Iterator[None]:
    """Vide le cache preview avant et après le test — évite les fuites inter-tests."""
    from server_fastapi.services.preview_cache import preview_cache

    # Accès direct à l'état interne : acceptable en tests.
    preview_cache._store.clear()  # noqa: SLF001
    yield
    preview_cache._store.clear()  # noqa: SLF001


@pytest.fixture
def reset_job_store() -> Iterator[None]:
    """Remet le store à zéro entre tests pour éviter les pollutions du verrou `active`."""
    from server_fastapi.services.job_store import job_store

    job_store._active = None  # noqa: SLF001
    job_store._jobs.clear()  # noqa: SLF001
    yield
    job_store._active = None  # noqa: SLF001
    job_store._jobs.clear()  # noqa: SLF001
