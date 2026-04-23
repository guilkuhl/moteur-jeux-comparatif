"""Tests smoke : healthz, openapi, algos catalogue."""
from __future__ import annotations


def test_healthz(client):
    # Spec: pixel-art-conversion-api § "Healthcheck"
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_openapi_exposed(client):
    # Spec: pixel-art-conversion-api § "OpenAPI exposé"
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    paths = spec.get("paths", {})
    assert "/api/convert" in paths
    assert "/api/preview" in paths
    assert "/api/bgmask" in paths


def test_algos_catalog(client):
    r = client.get("/api/algos")
    assert r.status_code == 200
    catalog = r.json()
    assert set(catalog.keys()) == {"sharpen", "scale2x", "denoise", "pixelsnap"}
    for algo, block in catalog.items():
        assert "methods" in block, f"{algo} sans methods"
        for method, meta in block["methods"].items():
            assert "params" in meta, f"{algo}/{method} sans params"


def test_request_id_header(client):
    """Le middleware request_id MUST poser X-Request-Id sur toute réponse."""
    r = client.get("/healthz")
    assert "x-request-id" in {k.lower() for k in r.headers}
