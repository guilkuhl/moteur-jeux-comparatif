"""Tests unitaires des services (sans FastAPI)."""
from __future__ import annotations

from PIL import Image

from server_fastapi.services.preview_cache import PreviewCache
from server_fastapi.services.upload import sanitize_basename, suggest_unused_name


def test_preview_cache_evicts_lru():
    cache = PreviewCache(max_size=2)
    img_a = Image.new("RGB", (2, 2), (10, 20, 30))
    img_b = Image.new("RGB", (2, 2), (40, 50, 60))
    img_c = Image.new("RGB", (2, 2), (70, 80, 90))
    cache.put(("a",), img_a)
    cache.put(("b",), img_b)
    cache.put(("c",), img_c)  # déclenche eviction de ("a",)
    assert cache.get(("a",)) is None
    assert cache.get(("b",)) is not None
    assert cache.get(("c",)) is not None


def test_preview_cache_step_key_deterministic():
    k1 = PreviewCache.step_key({"algo": "sharpen", "method": "unsharp_mask", "params": {"radius": 1.2, "percent": 200}})
    k2 = PreviewCache.step_key({"algo": "sharpen", "method": "unsharp_mask", "params": {"percent": 200, "radius": 1.2}})
    assert k1 == k2, "la clé doit être indépendante de l'ordre des params"


def test_sanitize_basename_strips_unsafe_chars():
    # Le sanitizer est destiné aux noms de fichiers uploadés — il remplace les
    # caractères hors whitelist (A-Za-z0-9._- et espace) par `_`.
    assert sanitize_basename("ok.png") == "ok.png"
    # Séquence de chars non-whitelistés → un seul `_`
    assert sanitize_basename("Foo#Bar!.png") == "Foo_Bar.png"
    assert sanitize_basename("") == "image"
    # Le stem reste non vide même si tout est filtré
    assert sanitize_basename("#@!.png").endswith(".png")
    # Les `.` internes sont conservés — c'est un sanitizer de basename, pas de path
    assert sanitize_basename("foo bar.tar.gz").startswith("foo bar")


def test_suggest_unused_name(tmp_path):
    (tmp_path / "foo.png").write_bytes(b"")
    (tmp_path / "foo-2.png").write_bytes(b"")
    assert suggest_unused_name("foo.png", tmp_path) == "foo-3.png"
