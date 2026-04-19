## ADDED Requirements

### Requirement: Le backend SHALL être un serveur Flask local lié strictement à 127.0.0.1
Le backend MUST être implémenté avec Flask dans `pixel-lab/server/app.py`, démarré sur `127.0.0.1` (jamais `0.0.0.0`) et écouter par défaut sur le port 5500. Il ne doit jamais importer le code des modules `algorithms/` : il orchestre uniquement via sous-processus.

#### Scenario: Bind localhost strict
- **GIVEN** le serveur Flask démarré
- **WHEN** on inspecte la socket d'écoute
- **THEN** elle SHALL être liée à `127.0.0.1:<port>` exclusivement, et toute requête depuis une autre machine SHALL recevoir une erreur de connexion réseau

#### Scenario: Aucune dépendance au code métier
- **GIVEN** le fichier `server/app.py`
- **WHEN** on lit ses imports
- **THEN** il SHALL n'importer aucun module de `pixel-lab/scripts/algorithms/` et n'utiliser que `subprocess`, `flask`, et la stdlib pour orchestrer

### Requirement: La route GET /api/inputs SHALL lister les images d'entrée
Le serveur MUST exposer `GET /api/inputs` qui renvoie la liste JSON des fichiers du dossier `pixel-lab/inputs/` dont l'extension appartient à `{.png, .jpg, .jpeg, .bmp, .webp, .tga}`.

#### Scenario: Liste des images
- **GIVEN** un dossier `inputs/` contenant 6 images
- **WHEN** un client appelle `GET /api/inputs`
- **THEN** la réponse SHALL être un JSON `{"images": [{"name": "...", "size": <bytes>, "processed": <bool>}, ...]}` avec un objet par image, le flag `processed` reflétant la présence d'au moins un run dans `history.json`

### Requirement: La route GET /api/algos SHALL exposer le catalogue des algorithmes et paramètres
Le serveur MUST exposer `GET /api/algos` qui renvoie un catalogue JSON construit à partir des dicts `METHODS` et `PARAMS` de chaque module `pixel-lab/scripts/algorithms/<algo>.py`. La réponse contient pour chaque algo la liste de ses méthodes et, par méthode, la liste des paramètres avec `{name, type, default, min, max}`.

#### Scenario: Catalogue complet
- **GIVEN** les 4 modules `sharpen`, `scale2x`, `denoise`, `pixelsnap`
- **WHEN** un client appelle `GET /api/algos`
- **THEN** la réponse SHALL être un JSON `{"algos": {"sharpen": {"methods": {"unsharp_mask": {"params": [{"name": "radius", "type": "float", "default": 1.2, "min": 0.1, "max": 10}, ...]}, ...}}, ...}}`

#### Scenario: Méthode sans paramètre
- **GIVEN** une méthode dont l'entrée `PARAMS` est vide ou absente
- **WHEN** le catalogue est sérialisé
- **THEN** la méthode SHALL apparaître avec une liste `params: []`, ce qui SHALL signaler au frontend qu'aucun champ n'est à afficher

### Requirement: La route POST /api/convert SHALL démarrer un job multi-images / multi-étapes
Le serveur MUST exposer `POST /api/convert` qui accepte un corps JSON `{images: [<basename>...], pipeline: [{algo, method, params: {...}}, ...]}`, démarre un job d'arrière-plan et renvoie immédiatement `202 Accepted` avec `{"job_id": "<uuid>"}`.

#### Scenario: Démarrage d'un job mono-étape
- **GIVEN** un payload valide `{images:["test_blurry.png"], pipeline:[{algo:"sharpen", method:"unsharp_mask", params:{radius:1.2,percent:200}}]}`
- **WHEN** le client envoie `POST /api/convert`
- **THEN** la réponse SHALL être `202` avec `{"job_id": "<uuid>"}` et un thread d'exécution SHALL être lancé en arrière-plan

#### Scenario: Démarrage d'un job pipeline
- **GIVEN** un payload `{images:["test_blurry.png","sprite.png"], pipeline:[{algo:"denoise",method:"median"},{algo:"pixelsnap",method:"median",params:{block:4}},{algo:"sharpen",method:"unsharp_mask"}]}`
- **WHEN** le client envoie la requête
- **THEN** le job SHALL planifier 2 images × 3 étapes = 6 sous-processus séquentiels par image (le job traite les images en parallèle ou séquentiellement selon configuration), et la réponse SHALL être `202` avec un seul `job_id`

### Requirement: La validation SHALL refuser les algos hors allow-list et les chemins suspects
Le serveur MUST valider chaque payload `POST /api/convert` AVANT de spawn un sous-processus :
- L'algo MUST appartenir à l'allow-list `{sharpen, scale2x, denoise, pixelsnap}` ; sinon la réponse SHALL être `400` avec `{"error": "unknown algo: <name>"}`.
- La méthode MUST exister dans `METHODS` du module ciblé ; sinon `400`.
- Chaque param MUST exister dans `PARAMS[<method>]` et sa valeur MUST respecter le type et les bornes `min`/`max` ; sinon `400` avec un message décrivant le param fautif.
- Chaque nom d'image MUST être un basename pur (sans `..`, sans `/`, sans `\`) et le fichier MUST exister dans `inputs/` ; sinon `400` avec `{"error": "invalid image: <name>"}`.

#### Scenario: Algo inconnu rejeté
- **GIVEN** un payload contenant `algo:"rm -rf /"`
- **WHEN** le serveur valide la requête
- **THEN** la réponse SHALL être `400` avec un message d'erreur explicite, et aucun sous-processus SHALL être lancé

#### Scenario: Path-traversal rejeté
- **GIVEN** un payload contenant `images: ["../../../etc/passwd"]`
- **WHEN** le serveur valide la requête
- **THEN** la réponse SHALL être `400` avec `{"error": "invalid image: ../../../etc/passwd"}`, et aucun accès au système de fichiers hors `inputs/` SHALL avoir lieu

#### Scenario: Param hors bornes rejeté
- **GIVEN** un payload `{algo:"pixelsnap", method:"median", params:{block:99999}}` alors que `PARAMS["median"]` déclare `max:32` pour `block`
- **WHEN** le serveur valide la requête
- **THEN** la réponse SHALL être `400` avec un message indiquant le param fautif, sa valeur reçue et la borne max attendue

### Requirement: La route GET /api/jobs/<id>/stream SHALL diffuser la progression via Server-Sent Events
Le serveur MUST exposer `GET /api/jobs/<id>/stream` retournant un flux SSE (`Content-Type: text/event-stream`). Le flux émet au minimum un événement par changement d'état d'image et un événement final `done` ou `error` à la fin du job.

#### Scenario: Flux SSE pour un job de 2 images × 3 étapes
- **GIVEN** un job en cours sur 2 images avec un pipeline de 3 étapes
- **WHEN** un client se connecte à `GET /api/jobs/<id>/stream`
- **THEN** le client SHALL recevoir au minimum les événements suivants en JSON : `{type:"step_start", image:"...", step:1}`, `{type:"step_done", image:"...", step:1, output:"..."}`, ..., `{type:"image_done", image:"..."}`, `{type:"done", success:2, errors:0}`

#### Scenario: Erreur dans une étape
- **GIVEN** une étape qui échoue (sous-processus retourne un code ≠ 0)
- **WHEN** l'étape se termine
- **THEN** un événement `{type:"step_error", image:"...", step:N, stderr:"..."}` SHALL être diffusé, le job SHALL passer à l'image suivante (sans interrompre le job global), et l'événement final `done` SHALL inclure le compteur `errors > 0`

### Requirement: L'orchestration SHALL chaîner les sous-processus en passant la sortie de l'étape N à l'étape N+1
Pour un pipeline multi-étapes, le serveur MUST appeler `python scripts/process.py <input> <algo> method=<m> [<params>...]` une fois par étape, en utilisant comme `<input>` le fichier `outputs/<image>/iter_NNN_*.png` produit par l'étape précédente.

#### Scenario: Chaînage des étapes
- **GIVEN** un pipeline de 2 étapes sur l'image `sprite.png`
- **WHEN** le job s'exécute
- **THEN** l'étape 1 SHALL être appelée avec `inputs/sprite.png` et produire `outputs/sprite/iter_NNN_<algo1>_<m1>.png`, puis l'étape 2 SHALL être appelée avec ce fichier comme entrée et produire `outputs/sprite/iter_NNN+1_<algo2>_<m2>.png`

#### Scenario: Warning scale2x au milieu
- **GIVEN** un pipeline `[denoise, scale2x, sharpen]` (scale2x change la résolution)
- **WHEN** le job s'exécute
- **THEN** un événement SSE `{type:"warning", message:"scale2x au milieu d'un pipeline, les étapes suivantes opèrent sur une image redimensionnée"}` SHALL être diffusé avant le `step_start` de l'étape `scale2x`, mais le pipeline SHALL continuer normalement
