## Why

Le back `pixel-lab/server/app.py` concentre aujourd'hui **1 476 lignes**, **22 routes** et ~60 fonctions helpers (validation, caches, history I/O, orchestrateur, upload, trash, zip export, autotile) dans un seul fichier Flask. Quatre limites concrètes :

1. **Validation dispersée et répétée** : `validate_payload`, `_validate_preview_payload`, et les validateurs inline (bgmask, inputs, outputs) appliquent les mêmes règles (`algo ∈ allow-list`, `method ∈ METHODS`, `params ∈ PARAMS[method]`, borne `min`/`max`) chacun à leur façon. Toute évolution doit être répliquée à ≥ 3 endroits.
2. **Pas de schéma machine-lisible** : le front code ses payloads à la main, le back répond en JSON ad-hoc. Aucun contrat `openapi.json`, donc impossible de générer des types front ou de les utiliser dans les tests e2e.
3. **Zéro test automatisé de routes** : seul `algorithms/test_params.py` existe. Les refactors (ex. `pixel-lab-backend-perf`) reposent sur des tests manuels `curl`.
4. **Framework de dev non prod-ready** : Flask `app.run(threaded=True)` reste, malgré l'ajout de `serve.py` gunicorn, sans middlewares propres (CORS, erreurs, timeouts, healthcheck).

FastAPI apporte nativement : validation Pydantic (un seul schéma par payload), `openapi.json` généré automatiquement, client de test intégré (`TestClient`), support ASGI uniforme (SSE via `StreamingResponse`, WebSocket si besoin plus tard), documentation `/docs` gratuite. Le travail utile (algos Pillow/NumPy) ne change pas — on garde l'import in-process de `apply_step.run_step`.

Décision utilisateur : **migration big bang** (une seule PR, un seul cutover) — jugée plus saine sur un outil localhost mono-utilisateur que de maintenir deux frameworks en parallèle (strangler fig).

## What Changes

- **NEW** `pixel-lab/server_fastapi/` : nouveau package remplaçant `server/` (l'ancien est supprimé en fin de migration). Organisation :
  - `main.py` : factory `create_app()`, middlewares (CORS strict localhost, exception handler JSON, request ID), healthcheck `/healthz`.
  - `routers/` : un router par domaine — `convert.py`, `preview.py`, `bgmask.py`, `inputs.py`, `outputs.py`, `history.py`, `autotile.py`, `spritesheet.py`.
  - `services/` : `pipeline_runner.py` (ex-`_run_job`), `preview_cache.py`, `bgmask_cache.py`, `history_store.py`, `upload.py`, `trash.py`. Aucune dépendance Flask, testables en isolation.
  - `schemas/` : modèles Pydantic v2 par payload (`PipelineStep`, `ConvertRequest`, `PreviewRequest`, `BgmaskQuery`, `AlgosResponse`, etc.). Source unique pour validation + OpenAPI.
  - `deps.py` : dépendances FastAPI (résolution d'image, lock `_active_job`, session DB si besoin futur).
- **MODIFIED** contrats API : **strictement identiques** côté payload/réponse/SSE/headers. Les seules évolutions visibles sont :
  - Format d'erreur de validation uniformisé : `{"errors": [{"loc": [...], "msg": "...", "type": "..."}]}` (Pydantic standard) au lieu du `{"errors": ["downscale: 10 hors bornes …"]}` bricolé. Le front doit adapter son rendu d'erreur (≤ 10 lignes JS).
  - `/docs` (Swagger) et `/openapi.json` ajoutés, pas de rupture.
- **MODIFIED** SSE `/api/jobs/<id>/stream` : implémenté via `fastapi.responses.StreamingResponse` + `async generator`. Les événements (`step_start`/`step_done`/`step_error`/`warning`/`image_done`/`done`) gardent **exactement** la même forme JSON (cf. change `pixel-lab-backend-perf`).
- **MODIFIED** entrée serveur : `pixel-lab/serve.py` lance `uvicorn server_fastapi.main:app` en dev (reload) ou via un wrapper gunicorn+uvicorn-worker en prod. `gunicorn>=21` + `uvicorn[standard]>=0.27` dans `requirements-prod.txt`.
- **MODIFIED** `pixel-lab/scripts/apply_step.py` : inchangé (déjà pur, indépendant du framework web). Continue d'être utilisé par `scripts/process.py` (CLI) et par le nouveau `services/pipeline_runner.py`.
- **REMOVED** `pixel-lab/server/app.py` et `pixel-lab/server/__init__.py` : supprimés en fin de migration (ou déplacés dans un tag git pour archive). Aucun import externe ne doit persister.
- **NEW** `pixel-lab/server_fastapi/tests/` : tests `pytest` minimum pour chaque router (happy path + un cas d'erreur de validation par route). Détail scope et objectif 100 % couverture déplacés dans le change `add-ci-e2e-tests`.
- **NEW** Middleware erreur global : toute exception non rattrapée renvoie `500` + payload `{"error":"internal","request_id":"<uuid>"}` avec log structuré. Remplace les essais/excepts éparpillés actuels.
- **PAS DE CHANGEMENT** : nommage `iter_NNN_*.png`, format `history.json`, cache preview (clé = `(basename, mtime_ns, downscale, steps_prefix)`), lock `_active_job`, CLI `scripts/process.py`.

## Capabilities

### New Capabilities
_Aucune nouvelle capability._ FastAPI remplace Flask sous le capot de `pixel-art-conversion-api`.

### Modified Capabilities
- `pixel-art-conversion-api` : implémentation passée de Flask à FastAPI, validation centralisée via Pydantic, OpenAPI exposé, tests pytest introduits. Contrats externes (routes, payloads, SSE, headers) préservés.

## Impact

- **Code touché**
  - Nouveau `pixel-lab/server_fastapi/` (~1 500 lignes réparties en ≤ 12 fichiers de ≤ 250 lignes).
  - Suppression `pixel-lab/server/app.py` (-1 476 lignes).
  - Adaptation `pixel-lab/serve.py` pour `uvicorn` (~30 lignes).
  - Adaptation `pixel-lab/requirements.txt` + `requirements-prod.txt` (FastAPI + uvicorn + Pydantic v2).
  - Adaptation légère front : format d'erreur Pydantic (≤ 10 lignes dans `dashboard/index.html`). Si le change `migrate-front-vue-spa` est livré dans la même fenêtre, l'adaptation est faite directement dans Vue.
- **APIs modifiées** : 0 rupture de route, 1 rupture de format d'erreur de validation (messages Pydantic vs strings custom). Nouvelles routes `/docs`, `/redoc`, `/openapi.json`, `/healthz`.
- **Dépendances** : ajout `fastapi>=0.110`, `uvicorn[standard]>=0.27`, `pydantic>=2.6`, `httpx>=0.27` (TestClient). Suppression `flask` de `requirements.txt`.
- **Sécurité** : CORS restreint à `http://127.0.0.1:5500` et `http://localhost:5500` par défaut (configurable via env). Bind strict `127.0.0.1` conservé. Validation Pydantic plus stricte que l'existant — moins de surface d'injection (types fortement typés).
- **Performance** : ASGI + uvicorn donne un overhead de routing comparable à Flask en usage mono-utilisateur. Gain réel : validation Pydantic en C (pydantic-core) plus rapide que les validateurs Python manuels actuels (~2-5× sur gros payloads).
- **Migration de données** : aucune. `history.json`, `outputs/`, `inputs/` inchangés.
- **Compatibilité descendante** : le script CLI `scripts/process.py` et ses consommateurs (`workflow.py`, `batch.py`) ne dépendent pas du framework web — zéro impact.
- **Rollback** : `git revert` du merge commit. Le change `pixel-lab-backend-perf` reste appliqué (in-process, PNG binaire) — ce change ne touche pas ces décisions.
