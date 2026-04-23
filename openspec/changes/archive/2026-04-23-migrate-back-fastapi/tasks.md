## 1. Scaffolding FastAPI

- [x] 1.1 Ajouter dans `pixel-lab/requirements.txt` : `fastapi>=0.110`, `uvicorn[standard]>=0.27`, `pydantic>=2.6`, `httpx>=0.27` (pour TestClient). Retirer `Flask` de `requirements.txt`
- [x] 1.2 Créer `pixel-lab/server_fastapi/__init__.py`, `main.py`, `deps.py` vides (squelettes)
- [x] 1.3 `main.py::create_app()` : instancie `FastAPI(title="Pixel Lab API", version="1.0.0")`, monte les middlewares (CORS `allow_origins=["http://127.0.0.1:5500","http://localhost:5500"]`, handler global d'exception → `{"error":"internal","request_id":<uuid>}`, middleware request_id qui pose un header `X-Request-Id`)
- [x] 1.4 Ajouter route `GET /healthz` qui renvoie `{"status":"ok","version":"1.0.0"}` — sert de smoke test CI
- [x] 1.5 Ajouter route `GET /openapi.json` (fourni par FastAPI, vérifier qu'elle existe bien)
- [x] 1.6 Lancer `uvicorn server_fastapi.main:app` manuellement, vérifier `/healthz` et `/docs` répondent

## 2. Schémas Pydantic

- [x] 2.1 Créer `server_fastapi/schemas/__init__.py`
- [x] 2.2 `schemas/pipeline.py` : `PipelineStep(algo: Literal[...], method: str, params: dict)`. Validator `@model_validator(mode="after")` qui vérifie `method ∈ METHODS[algo]`, cast des params via `apply_step._cast_params`, check des bornes `PARAMS[method]`
- [x] 2.3 `schemas/pipeline.py` : `ConvertRequest(images: list[str], pipeline: list[PipelineStep])`. Validator sur `images` : pas de `..`, pas de `/`, pas de `\`
- [x] 2.4 `schemas/pipeline.py` : `PreviewRequest(image: str, pipeline: list[PipelineStep], downscale: int | None = 256)`. Validator : `downscale ∈ [64, 4096] | None`
- [x] 2.5 `schemas/responses.py` : `JobCreatedResponse(job_id: str)`, `AlgosResponse` (nested dict algos → methods → params), `InputsResponse(files: list[InputFile])`, `ErrorResponse(error: str, request_id: str | None)`
- [x] 2.6 `schemas/bgmask.py` : `BgmaskQuery(image: str, tolerance: int = 8, feather: int = 0, mode: str = "highlight")`. Validators de bornes
- [x] 2.7 Tests `tests/test_schemas.py` : round-trip + cas d'erreurs de validation pour chaque schéma (≥ 3 cas par schéma)

## 3. Extraction des services (pure Python, sans FastAPI)

- [x] 3.1 `services/history_store.py` : `load()`, `save(dict)`, `append_image_runs(stem, runs)` avec `threading.Lock`. Remplace `_load_history`/`_save_history`/`_history_lock` de l'ancien `app.py`
- [x] 3.2 `services/preview_cache.py` : classe `PreviewCache(max_size=32)` avec `OrderedDict` + `threading.Lock`, API `get(key)`, `put(key, img)`, `step_key(step)`, `pipeline_cache_key(basename, mtime_ns, downscale, steps)`
- [x] 3.3 `services/bgmask_cache.py` : même pattern que preview_cache, max 16 entrées
- [x] 3.4 `services/pipeline_runner.py` : fonction `run_job(job_id, payload, event_queue)` qui contient la boucle `for img, for step: run_step(...)` de l'ancien `_run_job`. Pousse les événements dans `event_queue` (interface agnostique — pas de `_jobs[]` global)
- [x] 3.5 `services/job_store.py` : `JobStore` qui stocke `{job_id: asyncio.Queue}`, expose `create_job()`, `subscribe(job_id)` (async generator), `push(job_id, event)` (thread-safe via `loop.call_soon_threadsafe`). Lock `active_job` géré ici
- [x] 3.6 `services/upload.py` : logique de sauvegarde upload (sanitize basename, suggest unused name, extension allowlist). Extraite de l'ancien `app.py`
- [x] 3.7 `services/trash.py` : `move_to_trash(src, trash_root)`. Extraite de `app.py::_move_to_trash`
- [x] 3.8 Tests unitaires `tests/test_services/` : ≥ 1 test par service, sans FastAPI (utilise `tmp_path`, mocks)

## 4. Router `convert` + SSE

- [x] 4.1 `routers/convert.py::POST /api/convert` : valide `ConvertRequest`, appelle `job_store.create_job()`, lance `pipeline_runner.run_job` dans un `threading.Thread`, retourne `JobCreatedResponse` `202`
- [x] 4.2 `routers/convert.py::GET /api/jobs/{job_id}/stream` : `async def`, renvoie `StreamingResponse(event_gen(), media_type="text/event-stream")` qui consomme `job_store.subscribe(job_id)` et formate `"data: {json}\n\n"`
- [x] 4.3 Vérifier que les événements conservent exactement les champs : `step_start {image, step, algo, method}`, `step_done {image, step, output}`, `step_error {image, step, stderr}`, `image_done {image}`, `done`, `warning {message}` (cf. spec `pixel-art-conversion-api`)
- [x] 4.4 Verrou "un seul job actif" : `job_store.create_job()` retourne `409 Conflict` si un autre job est actif (comportement existant)
- [x] 4.5 Test `tests/test_convert.py::test_happy_path` : TestClient POST → attend `202` + `job_id`, puis lit le stream avec `httpx.AsyncClient`, vérifie la séquence `step_start` → `step_done` × N → `image_done` → `done`
- [x] 4.6 Test `tests/test_convert.py::test_validation_error` : payload avec algo inconnu → `422` avec détails Pydantic
- [x] 4.7 Test `tests/test_convert.py::test_concurrent_job_rejected` : 2 `POST /api/convert` en parallèle → le 2ᵉ renvoie `409`

## 5. Router `preview`

- [x] 5.1 `routers/preview.py::POST /api/preview` : valide `PreviewRequest`, consulte `preview_cache` pour le plus long préfixe, applique les étapes manquantes via `apply_step.run_step` en mémoire (pas de disque), écrit les préfixes dans le cache
- [x] 5.2 Réponse : `Response(png_bytes, media_type="image/png", headers={"X-Width":..., "X-Height":..., "X-Elapsed-Ms":..., "X-Cache-Hit-Depth":...})` — strictement identique au contrat du change `pixel-lab-backend-perf`
- [x] 5.3 Erreur de validation renvoie `422` avec corps JSON Pydantic (documenté comme rupture mineure vs l'ancien format `{"errors":[...strings]}`)
- [x] 5.4 Test `test_preview.py::test_binary_response` : `response.content` est un PNG valide (commence par `\x89PNG`), headers présents et cohérents
- [x] 5.5 Test `test_preview.py::test_cache_hit_depth` : 2 appels successifs avec préfixe partagé → `X-Cache-Hit-Depth` ≥ 1 au 2ᵉ

## 6. Router `bgmask`

- [x] 6.1 `routers/bgmask.py::GET /api/bgmask` : valide `BgmaskQuery` via `Depends`, résout image, appelle `bgdetect.compute_bg_mask` (import depuis `algorithms/`), applique le cache, renvoie `Response(png_bytes, media_type="image/png", headers={"X-Cache":..., "X-Bgmask-Color":...})`
- [x] 6.2 Test `test_bgmask.py::test_happy_path` + `test_cache_hit` + `test_out_of_range_tolerance`

## 7. Routers `inputs` / `outputs` / `history`

- [x] 7.1 `routers/inputs.py` : `GET /api/inputs`, `POST /api/inputs` (upload), `DELETE /api/inputs/<name>`. Utilise `services/upload.py` et `services/trash.py`
- [x] 7.2 `routers/outputs.py` : `DELETE /api/outputs/<stem>/<filename>`, `DELETE /api/outputs/<stem>`. Met à jour history via `history_store`
- [x] 7.3 `routers/history.py` : `GET /api/history`, `GET /api/algos` (construit depuis `ALGO_MODULES`)
- [x] 7.4 Tests happy path + validation par route (≥ 2 tests par router)

## 8. Routers `autotile` / `spritesheet`

- [x] 8.1 Migrer les routes autotile existantes (si présentes dans l'ancien `app.py`) en router dédié
- [x] 8.2 Migrer les routes spritesheet (slicing, export, cleanup, constraints) en router dédié
- [x] 8.3 Tests smoke par route (au moins 1 happy path chacune)

## 9. Entrée serveur et packaging

- [x] 9.1 Modifier `pixel-lab/serve.py` :
  - Dev : `uvicorn.run("server_fastapi.main:app", host="127.0.0.1", port=5500, reload=True)`
  - Prod (`PIXEL_LAB_PROD=1`) : `gunicorn` avec `-k uvicorn.workers.UvicornWorker -w 1 -b 127.0.0.1:5500 server_fastapi.main:app`
- [x] 9.2 Adapter `requirements-prod.txt` : ajouter `uvicorn[standard]>=0.27` (gunicorn déjà présent)
- [x] 9.3 Mettre à jour `pixel-lab/README.md` : section « Lancement » parle d'uvicorn, mention `/docs` et `/openapi.json`, note sur `-w 1`
- [x] 9.4 Smoke test : `python pixel-lab/serve.py` → ouvrir `http://127.0.0.1:5500/docs` → vérifier toutes les routes listées

## 10. Cutover

- [x] 10.1 Supprimer `pixel-lab/server/app.py` et `pixel-lab/server/__init__.py`
- [x] 10.2 Dans `pixel-lab/dashboard/index.html`, adapter la gestion d'erreur validation : `data.errors.map(e => typeof e === 'string' ? e : e.msg).join(' · ')` (compat rétro legère, supprime l'hypothèse string-only)
- [x] 10.3 Vérifier qu'aucun import `from server.app` ou `from flask` ne subsiste (`rg "from flask|from server\\.app"` → 0 match)
- [x] 10.4 Retirer `Flask` de `requirements.txt` si pas déjà fait

## 11. Validation de non-régression

- [x] 11.1 Lancer un batch de référence (10 images × 3 étapes via dashboard) avant cutover, sauvegarder `outputs/` et `history.json`
- [x] 11.2 Après cutover, relancer le même batch, faire `diff -r` sur `outputs/` : doit être bit-à-bit identique (hors timestamps de `history.json`)
- [x] 11.3 Vérifier `curl http://127.0.0.1:5500/api/jobs/<id>/stream` → événements JSON identiques à la référence d'avant migration
- [x] 11.4 Test UI manuel : upload → preview live → convert → delete → zip export — tous verts
- [x] 11.5 `pytest pixel-lab/server_fastapi/tests/` → 100 % pass
