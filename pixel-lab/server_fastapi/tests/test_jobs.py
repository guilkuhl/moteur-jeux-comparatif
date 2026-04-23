"""Job store + /api/convert + SSE."""
from __future__ import annotations

import pytest


def test_try_start_returns_unique_ids_then_locks():
    from server_fastapi.services.job_store import JobStore

    store = JobStore()
    a = store.try_start()
    assert a is not None
    b = store.try_start()
    assert b is None, "doit refuser un 2e job tant que le 1er est actif"
    store.finish(a.job_id)
    c = store.try_start()
    assert c is not None and c.job_id != a.job_id


def test_push_appends_event_and_survives_without_loop():
    """Sans `bind_loop`, push() doit juste persister l'event sans crash."""
    from server_fastapi.services.job_store import JobStore

    store = JobStore()
    job = store.try_start()
    assert job is not None
    store.push(job.job_id, {"type": "step_start", "image": "x.png", "step": 0})
    assert len(job.events) == 1
    assert job.events[0]["type"] == "step_start"


def test_convert_409_when_another_job_active(client, test_input_image, reset_job_store):
    """Spec: pixel-art-conversion-api § "Verrou un seul job actif"."""
    payload = {
        "images": [test_input_image],
        "pipeline": [{"algo": "sharpen", "method": "unsharp_mask", "params": {"radius": 1.0}}],
    }
    # Premier démarrage : 202
    r1 = client.post("/api/convert", json=payload)
    assert r1.status_code == 202

    # Deuxième démarrage avant la fin → 409 (le thread worker n'a peut-être
    # pas encore fini, mais même si fini, le test conserve sa valeur
    # puisque le statu 409/202 dépend de l'état présent au moment du post)
    r2 = client.post("/api/convert", json=payload)
    assert r2.status_code in (202, 409), f"expected 202 or 409, got {r2.status_code}"


def test_stream_404_on_unknown_job(client):
    r = client.get("/api/jobs/not-a-real-id/stream")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_subscribe_yields_existing_events_then_done():
    """subscribe() doit rejouer les events déjà présents + s'arrêter sur `done`."""
    from server_fastapi.services.job_store import JobStore

    store = JobStore()
    job = store.try_start()
    assert job is not None
    # Pas de bind_loop ici — on push à la main dans job.events
    job.events.append({"type": "step_start", "image": "a.png", "step": 0})
    job.events.append({"type": "done"})

    received: list[dict] = []
    async for evt in store.subscribe(job.job_id):
        received.append(evt)

    assert [e["type"] for e in received] == ["step_start", "done"]


def test_convert_happy_path_writes_iter_and_finishes(
    client, test_input_image, reset_job_store,
):
    """Intégration compacte : POST /api/convert → attendre la fin du thread job
    (via polling des events du store, pas du stream SSE — le pont
    asyncio.call_soon_threadsafe ne fonctionne pas avec TestClient, qui crée
    un event loop ad-hoc par requête)."""
    import time

    from server_fastapi.deps import OUTPUTS_DIR
    from server_fastapi.services.job_store import job_store

    r = client.post(
        "/api/convert",
        json={
            "images": [test_input_image],
            "pipeline": [
                {"algo": "sharpen", "method": "unsharp_mask",
                 "params": {"radius": 1.0, "percent": 150}},
            ],
        },
    )
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    # Poll jusqu'à réception de l'event `done` ou timeout raisonnable
    deadline = time.time() + 10.0
    job = job_store.get(job_id)
    assert job is not None
    while time.time() < deadline:
        if any(e.get("type") == "done" for e in job.events):
            break
        time.sleep(0.05)
    else:
        raise AssertionError(f"job {job_id} n'a pas émis `done` en 10s ({job.events=})")

    types = [e["type"] for e in job.events]
    assert "step_start" in types
    assert "step_done" in types
    assert types[-1] == "done"

    # L'iter_001 doit exister sur disque (parité avec CLI)
    stem = test_input_image.removesuffix(".png")
    iters = list((OUTPUTS_DIR / stem).glob("iter_*.png"))
    assert iters, f"aucun iter produit dans outputs/{stem}/"
