"""Fixtures pytest partagées."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture
def client() -> TestClient:
    from server_fastapi.main import app
    return TestClient(app)


@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    """Génère un petit PNG 8x8 déterministe dans `tmp_path`."""
    img = Image.new("RGBA", (8, 8), (100, 150, 200, 255))
    p = tmp_path / "sample.png"
    img.save(p)
    return p
