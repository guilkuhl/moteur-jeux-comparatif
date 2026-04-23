## Context

Post `pixel-lab-backend-perf`, le back est **in-process** (plus de subprocess dans `/api/convert`), avec un module partagé `scripts/apply_step.py`. Les contrats sont stables. C'est le bon moment pour migrer l'infra web (Flask → FastAPI) sans remixer le contrat métier.

L'application est **localhost mono-utilisateur** : pas de scale horizontal, pas d'auth, pas de multi-tenant. Les contraintes qui justifieraient de rester sur Flask (écosystème de legacy, stabilité API depuis 2010) ne s'appliquent pas. Les bénéfices attendus de FastAPI se concentrent sur la **qualité de développement** : validation centralisée, types, tests, docs.

## Goals / Non-Goals

**Goals:**
- Remplacer Flask par FastAPI sans rupture des contrats API externes (sauf format d'erreur de validation, documenté).
- Centraliser la validation dans des schémas Pydantic réutilisables (1 schéma = 1 source de vérité).
- Exposer `openapi.json` et `/docs` pour outiller le front et la doc.
- Introduire une base de tests pytest (≥ 1 happy path + 1 erreur par route).
- Découper `app.py` en modules cohérents (routers par domaine, services, schemas).
- Préserver le comportement in-process de `/api/convert` et le format binaire de `/api/preview`.

**Non-Goals:**
- Pas de passage à WebSocket : SSE reste le canal d'événements (décision utilisateur).
- Pas d'auth / rate-limit : outil localhost, surface inchangée.
- Pas de base de données : `history.json` et le FS restent la source.
- Pas de micro-services : un seul process ASGI.
- Pas de refacto des algorithmes : `apply_step.run_step` est déjà propre.
- Pas de migration front dans ce change (géré par `migrate-front-vue-spa`).

## Decisions

### D1. Framework : FastAPI (vs Flask + Flask-RESTX, vs Starlette nu)

**Choix :** FastAPI 0.110+.

**Pourquoi :**
- Pydantic v2 natif → validation + OpenAPI + types Python en un seul schéma.
- Support ASGI uniforme (SSE via `StreamingResponse`, WS futur possible).
- Testabilité native (`TestClient` basé sur httpx).
- Documentation automatique (`/docs`, `/redoc`).
- Écosystème mature (starlette, uvicorn, httpx) — stack cohérente.

**Alternatives considérées :**
- **Flask + pydantic + apispec** : possible mais re-bricole ce que FastAPI offre natif.
- **Starlette nu** : plus léger mais sans injection de dépendances ni doc auto — reconstruire FastAPI soi-même.
- **Litestar** : techniquement excellent, mais écosystème et adoption plus petits — moins de ressources pour débogage et recrutement.

### D2. Découpage en routers / services / schemas

**Choix :** arborescence standard FastAPI :
```
server_fastapi/
├── main.py              # create_app(), middlewares, healthcheck
├── deps.py              # dépendances partagées (resolve_input, history_lock, …)
├── schemas/
│   ├── __init__.py
│   ├── pipeline.py      # PipelineStep, ConvertRequest, PreviewRequest
│   ├── errors.py        # ErrorResponse standard
│   └── responses.py     # AlgosResponse, InputsResponse, …
├── routers/
│   ├── convert.py       # POST /api/convert, GET /api/jobs/<id>/stream
│   ├── preview.py       # POST /api/preview
│   ├── bgmask.py        # GET /api/bgmask
│   ├── inputs.py        # GET/POST/DELETE /api/inputs
│   ├── outputs.py       # DELETE /api/outputs
│   ├── history.py       # GET /api/history, /api/algos
│   ├── autotile.py      # routes auto-tile
│   └── spritesheet.py   # routes spritesheet
├── services/
│   ├── pipeline_runner.py   # _run_job (async via thread exécuteur)
│   ├── preview_cache.py
│   ├── bgmask_cache.py
│   ├── history_store.py
│   ├── upload.py
│   └── trash.py
└── tests/
    ├── conftest.py
    ├── test_convert.py
    ├── test_preview.py
    └── …
```

**Pourquoi :**
- Chaque fichier ≤ 250 lignes → navigable, reviewable.
- Services sans dépendance FastAPI → testables en unitaire sans `TestClient`.
- Routers fins : validation Pydantic + appel service + sérialisation. Pas de logique.
- Schemas au centre : consommés par routers, services, tests, et (via OpenAPI) le front.

**Alternatives considérées :**
- Structure "module plat" (tout dans `main.py` + `routes.py`) — rejeté, on retombe dans l'anti-pattern de `app.py:1476`.
- Découper par route individuelle (`routers/convert_post.py`, etc.) — trop granulaire, disperse le contexte.

### D3. SSE : `StreamingResponse` + thread-safe queue

**Choix :** le job tourne dans un thread (comme aujourd'hui — NumPy/Pillow relâchent le GIL, async I/O ne gagne rien). La route SSE lit depuis une `asyncio.Queue` alimentée par un `loop.call_soon_threadsafe` dans le thread job.

```python
@router.get("/api/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    async def event_gen():
        async for evt in job_store.subscribe(job_id):
            yield f"data: {json.dumps(evt)}\n\n"
    return StreamingResponse(event_gen(), media_type="text/event-stream")
```

**Pourquoi :**
- Le contrat SSE côté client (EventSource) est strictement préservé.
- Pas besoin de convertir les algos en async — ils restent synchrones CPU-bound.
- `asyncio.Queue` fait le pont thread → event loop proprement.

**Alternatives considérées :**
- Exécution du job en async natif — impose de rewrapper Pillow/NumPy en `run_in_executor` partout, verbeux.
- Migration vers WebSocket — refusé par l'utilisateur, casserait le client existant.

### D4. Validation : Pydantic v2 comme source unique

**Choix :** un schéma Pydantic par payload. Les règles métier (bornes des params selon `PARAMS[method]`) sont implémentées en **validateur dynamique** qui consulte les modules `algorithms/` :

```python
class PipelineStep(BaseModel):
    algo: Literal["sharpen", "scale2x", "denoise", "pixelsnap"]
    method: str
    params: dict[str, Any] = {}

    @model_validator(mode="after")
    def check_method_and_params(self) -> "PipelineStep":
        mod = ALGO_MODULES[self.algo]
        if self.method not in mod.METHODS:
            raise ValueError(f"méthode inconnue '{self.method}' pour {self.algo}")
        self.params = _cast_and_bound_check(self.algo, self.method, self.params)
        return self
```

**Pourquoi :**
- Une seule définition ⇒ OpenAPI + validation + typing + docs.
- Les erreurs Pydantic sont précises (`loc`, `type`, `msg`).
- Le cast int/float/bool est centralisé dans `apply_step._cast_params` (déjà fait).

**Trade-off :** format d'erreur change. Aujourd'hui : `["downscale: 10 hors bornes [64, 4096]"]`. Demain : `[{"loc":["body","downscale"],"msg":"Input should be between 64 and 4096","type":"greater_than_equal"}]`. Le front doit joindre les messages (`errors.map(e => e.msg).join(" · ")`) — adaptation triviale.

### D5. Entrée serveur : uvicorn en dev, gunicorn+uvicorn-worker en prod

**Choix :** `pixel-lab/serve.py` revu :
- `PIXEL_LAB_PROD=1` → `gunicorn server_fastapi.main:app -k uvicorn.workers.UvicornWorker -w 1 -b 127.0.0.1:5500` (toujours `-w 1` : voir caveat `_active_job`).
- Sinon → `uvicorn server_fastapi.main:app --host 127.0.0.1 --port 5500 --reload`.

**Pourquoi :**
- uvicorn en dev → reload auto au save (meilleure DX que `app.run`).
- gunicorn+UvicornWorker en prod → supervision mature, timeouts worker, graceful shutdown.
- `-w 1` conservé : `_active_job` et caches restent des globaux process.

### D6. Stratégie big bang (vs strangler fig)

**Choix utilisateur :** big bang.

**Plan :**
1. `server_fastapi/` développé en parallèle (feature branch).
2. Tests pytest `≥ 1 route × 2 cas` verts localement.
3. Lancement manuel `uvicorn` → smoke test dashboard (préservé tant que `migrate-front-vue-spa` pas mergé).
4. Même PR : suppression `server/app.py`, mise à jour `serve.py`, mise à jour `README.md`.
5. Ajustement format d'erreur côté `dashboard/index.html` (ou attendre que le change Vue arrive — à coordonner).

**Trade-off :** une seule PR large (~1 500 lignes add, ~1 476 lignes del). Mitigation : commits atomiques (router par router) dans la branche avant le PR final.

### D7. Tests pytest livrés dans ce change (minimum vital)

**Choix :** ≥ 1 happy path + ≥ 1 cas d'erreur de validation par route principale (convert, preview, bgmask, inputs POST/DELETE, outputs DELETE, algos). Utilisation de `TestClient` + fixtures `tmp_path` pour isoler `inputs/`/`outputs/`.

**Pourquoi :**
- Sans tests, le big bang est un pari.
- Les scénarios d'OpenSpec servent de spec de test (1 scénario = 1 test).
- `TestClient` FastAPI est synchrone et ergonomique, pas de surcoût d'infra.

**Couverture cible V1 :** 60 % sur les routers. La couverture exhaustive et les tests e2e Playwright vivent dans le change `add-ci-e2e-tests`.

## Risks / Trade-offs

- **[Rupture format d'erreur de validation]** → le front existant lit `data.errors` comme `string[]`. Mitigation : la PR modifie `dashboard/index.html` dans le même commit (ou le change Vue arrive en même temps). Documenté dans le scenario de spec dédié.
- **[SSE async ↔ thread job : fuite de queue]** → si un client abandonne sans consommer, la queue grossit. Mitigation : utiliser `asyncio.Queue(maxsize=1000)` et dropper les plus anciens si saturé, plus timeout subscribe.
- **[`_active_job` mémoire process, gunicorn multi-worker casserait]** → inchangé depuis le change précédent. Reste `-w 1`, commenté dans `serve.py`.
- **[Pydantic v2 stricte sur les entiers/flottants]** → le front JS envoie parfois `1` là où Pydantic attend `1.0`. Mitigation : `float` dans les schémas, ou `Annotated[float, BeforeValidator(float)]`. Test e2e valide.
- **[Surcharge OpenAPI : l'endpoint `/openapi.json` expose les routes]** → considéré OK pour un outil localhost. Sinon désactivable via `FastAPI(openapi_url=None)`.
- **[TestClient n'exécute pas le SSE streaming comme un vrai client]** → un test smoke spécifique avec `httpx.AsyncClient` + `response.aiter_lines()` est ajouté pour la route SSE.

## Migration Plan

1. **Phase 1 — Scaffolding** : créer l'arborescence `server_fastapi/` vide, installer `fastapi`, `uvicorn`, `pydantic>=2`. `main.py` avec `create_app()` + healthcheck `/healthz` + CORS localhost. `pytest` passe à vide.
2. **Phase 2 — Schémas** : écrire tous les schémas Pydantic (`schemas/pipeline.py`, `schemas/responses.py`). Tests unitaires de sérialisation.
3. **Phase 3 — Services extraits** : déplacer la logique `_run_job`, caches, history I/O, upload, trash dans `services/` — sans dépendance Flask, testés en unitaire. Zéro changement comportemental.
4. **Phase 4 — Routers** : implémenter chaque router FastAPI en consommant les services + schémas. Routes migrées 1 par 1, commit par commit. TestClient happy path + erreur par route.
5. **Phase 5 — SSE** : implémenter `StreamingResponse` + `asyncio.Queue`. Test smoke avec `httpx.AsyncClient`.
6. **Phase 6 — Entrée serveur** : adapter `serve.py` (uvicorn/gunicorn-uvicorn-worker), mettre à jour `requirements*.txt` et `README.md`.
7. **Phase 7 — Cutover** : supprimer `server/app.py` et `server/__init__.py`. Adapter le format d'erreur dans `dashboard/index.html` (ou coordonner avec le change Vue). Commit de bascule unique.
8. **Phase 8 — Vérification** : smoke test complet (upload, convert 10 img × 3 steps, preview live, bgmask, delete, zip export). Comparer bit-à-bit les `iter_NNN_*.png` et `history.json` à une référence pré-migration.

Rollback : `git revert` du merge. Le change `pixel-lab-backend-perf` reste intact (il est purement logique, pas framework-dépendant via `apply_step.py`).

## Open Questions

- **Version Pydantic v1 vs v2** : v2 recommandé (perf + API plus claire), mais v1 a un écosystème encore plus large. Décision : **v2**, arrivé à maturité depuis 2023.
- **Activer `/docs` publiquement en prod ?** : en localhost, OK. Si un jour on expose le service, il faudra gater derrière une env var.
- **Adopter `httpx` comme client interne pour les tests Playwright aussi ?** : probablement oui, traité dans `add-ci-e2e-tests`.
- **Strict mode Pydantic pour refuser les champs non déclarés ?** : oui par défaut (`model_config = ConfigDict(extra="forbid")`) — protège contre le drift silencieux des payloads.
- **Générer des types TS côté front via openapi-typescript ?** : hors scope V1 (utilisateur n'a pas coché l'option « contrat OpenAPI partagé »). À reconsidérer après livraison Vue.
