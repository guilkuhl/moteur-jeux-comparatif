## MODIFIED Requirements

### Requirement: Le backend SHALL être une application ASGI FastAPI liée strictement à 127.0.0.1
Le backend MUST être implémenté avec FastAPI 0.110+ dans `pixel-lab/server_fastapi/`, démarré sur `127.0.0.1` (jamais `0.0.0.0`) et écouter par défaut sur le port 5500. L'application MUST être structurée en :
- `main.py::create_app()` comme factory
- `routers/` pour les endpoints, groupés par domaine (convert, preview, bgmask, inputs, outputs, history, autotile, spritesheet)
- `services/` pour la logique métier sans dépendance FastAPI (pipeline runner, caches, history store, upload, trash, job store)
- `schemas/` pour les modèles Pydantic v2 utilisés en validation et exposés via `/openapi.json`

Le backend MUST exposer :
- `GET /healthz` qui renvoie `{"status":"ok","version":"<semver>"}`
- `GET /openapi.json` (schéma OpenAPI complet auto-généré)
- `GET /docs` (Swagger UI)

Le backend MUST importer directement `apply_step.run_step` pour exécuter les étapes de pipeline in-process (aucun `subprocess.Popen` de `process.py` depuis les routes API).

#### Scenario: Bind localhost strict
- **GIVEN** le serveur uvicorn démarré
- **WHEN** on inspecte la socket d'écoute
- **THEN** elle SHALL être liée à `127.0.0.1:<port>` exclusivement, et toute requête depuis une autre machine SHALL recevoir une erreur de connexion réseau

#### Scenario: OpenAPI exposé
- **GIVEN** le backend démarré
- **WHEN** un client appelle `GET /openapi.json`
- **THEN** la réponse SHALL être `200 OK` avec `Content-Type: application/json` et le corps SHALL contenir la définition OpenAPI 3.1 avec au minimum les chemins `/api/convert`, `/api/preview`, `/api/bgmask`, `/api/inputs`, `/api/algos`, `/api/jobs/{job_id}/stream` et leurs schémas `requestBody`/`responses`

#### Scenario: Healthcheck
- **GIVEN** le backend démarré
- **WHEN** un client appelle `GET /healthz`
- **THEN** la réponse SHALL être `200 OK` avec un JSON `{"status":"ok"}` (la présence de ce endpoint est utilisée par le CI comme gate de smoke test)

#### Scenario: Exécution in-process via le module partagé
- **GIVEN** le fichier `server_fastapi/services/pipeline_runner.py`
- **WHEN** on lit ses imports
- **THEN** il SHALL importer `run_step` depuis `scripts/apply_step.py` et utiliser les modules `algorithms/*.py` via ce module partagé ; il SHALL NOT lancer `subprocess.Popen` pour invoquer `scripts/process.py`

### Requirement: La validation des payloads SHALL être centralisée dans des schémas Pydantic v2
Toutes les validations de corps de requête et de query parameters MUST être portées par des schémas Pydantic v2 dans `server_fastapi/schemas/`. Les règles métier (algo ∈ allow-list, method ∈ `METHODS[algo]`, bornes `PARAMS[method]`, interdiction des chemins traversants) MUST être implémentées comme `model_validator` ou `field_validator` dans ces schémas, **une seule fois**, et réutilisées par toutes les routes qui acceptent un pipeline (au minimum `POST /api/convert` et `POST /api/preview`).

En cas de violation, la réponse MUST être `422 Unprocessable Entity` avec un corps JSON au format Pydantic standard :
```json
{"errors": [{"loc": ["body", "pipeline", 0, "algo"], "msg": "...", "type": "literal_error"}]}
```

#### Scenario: Algo inconnu rejeté par le schéma
- **GIVEN** un payload `POST /api/convert` avec `pipeline:[{algo:"rm_rf","method":"root"}]`
- **WHEN** FastAPI valide la requête via `ConvertRequest`
- **THEN** la réponse SHALL être `422` avec `{"errors":[{"loc":["body","pipeline",0,"algo"], ...}]}` avant toute exécution métier

#### Scenario: Path-traversal sur le nom d'image rejeté
- **GIVEN** un payload `POST /api/convert` avec `images:["../../../etc/passwd"]`
- **WHEN** le validateur Pydantic s'exécute
- **THEN** la réponse SHALL être `422` indiquant que `images[0]` doit être un basename pur (pas de `..`, `/`, `\`)

#### Scenario: Paramètre hors bornes rejeté
- **GIVEN** un payload avec un step `{algo:"pixelsnap",method:"median",params:{block:99999}}` alors que `PARAMS["median"]["block"].max == 32`
- **WHEN** le validateur s'exécute
- **THEN** la réponse SHALL être `422` avec `loc:["body","pipeline",0,"params","block"]` et un message mentionnant la borne max attendue

#### Scenario: Schéma unique partagé entre /api/convert et /api/preview
- **GIVEN** les schémas `PipelineStep` et `ConvertRequest`/`PreviewRequest`
- **WHEN** on inspecte les routers
- **THEN** les deux routes SHALL consommer le même modèle `PipelineStep` pour valider leurs étapes, et une modification de ce modèle SHALL se refléter dans les deux endpoints sans duplication de code

### Requirement: Les événements SSE SHALL être diffusés via StreamingResponse et une queue thread-safe
Le serveur MUST exposer `GET /api/jobs/{job_id}/stream` qui renvoie une `StreamingResponse` de type `text/event-stream`. Le job s'exécute dans un thread worker ; les événements sont poussés dans une `asyncio.Queue` (via `loop.call_soon_threadsafe`) et consommés par un `async generator` côté route. Les types d'événements et la forme JSON de chaque événement MUST rester identiques au comportement existant : `step_start {image, step, algo, method}`, `step_done {image, step, output}`, `step_error {image, step, stderr}`, `warning {message}`, `image_done {image}`, `done`.

#### Scenario: Flux SSE pour un job multi-étapes
- **GIVEN** un job `/api/convert` sur 1 image × 3 étapes
- **WHEN** un client se connecte à `GET /api/jobs/{job_id}/stream`
- **THEN** le client SHALL recevoir dans l'ordre : 3× `step_start`, 3× `step_done`, 1× `image_done`, 1× `done`, chacun sous forme `data: {json}\n\n`

#### Scenario: Déconnexion client propre
- **GIVEN** un client qui abandonne sa connexion SSE en milieu de job
- **WHEN** la coroutine `event_gen()` détecte la déconnexion
- **THEN** elle SHALL annuler proprement sa subscription à `job_store`, libérer la queue associée, et le job SHALL continuer en arrière-plan sans erreur

### Requirement: Le serveur SHALL être lancé via uvicorn en dev et gunicorn+UvicornWorker en prod
Le script `pixel-lab/serve.py` MUST :
- En dev (par défaut) : lancer `uvicorn server_fastapi.main:app --host 127.0.0.1 --port 5500 --reload`
- En prod (`PIXEL_LAB_PROD=1`) : lancer `gunicorn -k uvicorn.workers.UvicornWorker -w 1 -b 127.0.0.1:5500 server_fastapi.main:app`

Le nombre de workers MUST rester à `1` tant que `job_store.active_job` et les caches (`preview_cache`, `bgmask_cache`) sont des états en mémoire process. Un commentaire explicite dans `serve.py` MUST rappeler ce caveat.

#### Scenario: Mode dev avec reload
- **GIVEN** l'absence de la variable d'environnement `PIXEL_LAB_PROD`
- **WHEN** on exécute `python pixel-lab/serve.py`
- **THEN** uvicorn SHALL démarrer avec `--reload` et toute modification d'un fichier `.py` sous `server_fastapi/` SHALL déclencher un redémarrage automatique du process

#### Scenario: Mode prod -w 1
- **GIVEN** `PIXEL_LAB_PROD=1` et `gunicorn` installé
- **WHEN** on exécute `python pixel-lab/serve.py`
- **THEN** gunicorn SHALL démarrer avec `-w 1 -k uvicorn.workers.UvicornWorker`, un seul worker SHALL être forké, et les logs SHALL confirmer le bind `127.0.0.1:5500`
