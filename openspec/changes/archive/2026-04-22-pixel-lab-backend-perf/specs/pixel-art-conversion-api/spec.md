## MODIFIED Requirements

### Requirement: La route POST /api/convert SHALL exécuter ses pipelines in-process sans spawn de subprocess Python
Le serveur MUST exécuter chaque étape de pipeline de `/api/convert` dans le process Flask via un appel de fonction direct (module partagé `scripts/apply_step.py`), sans passer par `subprocess.Popen(sys.executable, "scripts/process.py", …)`. Le contrat externe (payload JSON, format SSE, nommage `iter_NNN_<algo>_<method>.png`, structure `history.json`) MUST rester strictement identique au comportement antérieur. Le verrou `_active_job` garantissant un seul job actif à la fois MUST être conservé.

#### Scenario: Pipeline multi-étapes exécuté en-process
- **GIVEN** un payload valide `{images:["sprite.png"], pipeline:[{algo:"pixelsnap",method:"block",params:{size:2}},{algo:"denoise",method:"median",params:{size:3}},{algo:"sharpen",method:"unsharp_mask",params:{radius:1.2,percent:200}}]}`
- **WHEN** le client envoie `POST /api/convert`
- **THEN** le serveur SHALL répondre `202 Accepted` avec un `job_id`, puis pour chaque étape SHALL appeler `run_step` en-process (aucun `subprocess.Popen` pour invoquer `process.py` n'est déclenché par `/api/convert`), ET trois fichiers `iter_NNN_pixelsnap_block.png`, `iter_NNN_denoise_median.png`, `iter_NNN_sharpen_unsharp_mask.png` SHALL être écrits dans `outputs/sprite/` avec la même convention de nommage qu'avant le refactor

#### Scenario: Événements SSE inchangés
- **GIVEN** un job `/api/convert` en cours
- **WHEN** un client écoute `/api/jobs/<job_id>/stream`
- **THEN** les événements reçus SHALL conserver exactement les types et champs historiques : `step_start {image, step, algo, method}`, `step_done {image, step, output}`, `step_error {image, step, stderr}` (le champ `stderr` contient désormais le message d'exception Python tronqué à 500 chars au lieu de la stderr d'un subprocess, mais le **nom du champ** reste `stderr` pour compatibilité client), `image_done {image}`, `done`, `warning {message}`

#### Scenario: Parité bit-à-bit avec l'ancien chemin
- **GIVEN** une image de référence `sprite.png` et un pipeline figé `[{algo:"sharpen",method:"unsharp_mask",params:{radius:1.2,percent:200}}]`
- **WHEN** le même payload est soumis à `/api/convert` avant et après le refactor
- **THEN** le fichier `iter_001_sharpen_unsharp_mask.png` produit SHALL être identique bit-à-bit (`cmp` retourne 0), et l'entrée correspondante dans `history.json` SHALL contenir les mêmes champs `{algo, method, params, output}` (timestamps exclus)

#### Scenario: Gestion d'erreur par étape
- **GIVEN** un pipeline dont la 2ᵉ étape déclenche une exception dans l'algorithme (ex. param hors bornes non attrapé par la validation statique)
- **WHEN** `run_step` remonte l'exception
- **THEN** le serveur SHALL pousser un événement SSE `step_error {image, step: 1, stderr: "<message tronqué 500 chars>"}`, SHALL ne pas écrire le `iter_NNN_*.png` de cette étape, ET SHALL continuer sur la 3ᵉ étape (comportement `continue` actuel de `_run_job`)

### Requirement: La route POST /api/preview SHALL retourner un PNG binaire avec métadonnées en headers HTTP
Le serveur MUST renvoyer la réponse de `POST /api/preview` en tant que PNG binaire (`Content-Type: image/png`) dans le corps de la réponse, avec les métadonnées dans des headers HTTP personnalisés : `X-Width`, `X-Height`, `X-Elapsed-Ms`, `X-Cache-Hit-Depth`. L'encodage base64 et le wrapper JSON `{"png_base64": …}` MUST être supprimés. Les réponses d'erreur (400, 404, 409, 413, etc.) MUST continuer à utiliser le format JSON `{"errors": [...]}` ou `{"error": "..."}` comme aujourd'hui.

#### Scenario: Réponse réussie au format binaire
- **GIVEN** un payload valide `{image:"sprite.png", pipeline:[{algo:"sharpen",method:"unsharp_mask",params:{radius:1.0,percent:150}}], downscale:256}`
- **WHEN** le client envoie `POST /api/preview`
- **THEN** la réponse SHALL être `200 OK` avec `Content-Type: image/png`, le corps SHALL être un PNG valide décodable par Pillow/navigateur, ET les headers SHALL inclure `X-Width`, `X-Height`, `X-Elapsed-Ms`, `X-Cache-Hit-Depth` avec des valeurs entières

#### Scenario: Header de cache hit
- **GIVEN** un premier appel `/api/preview` avec pipeline `[A, B]` puis un second avec pipeline `[A, B, C]` (préfixe identique)
- **WHEN** le serveur traite le second appel
- **THEN** la réponse `200 OK` SHALL contenir `X-Cache-Hit-Depth: 2` (deux étapes récupérées depuis le cache)

#### Scenario: Erreur de validation reste en JSON
- **GIVEN** un payload avec `downscale: 10` (hors bornes [64, 4096])
- **WHEN** le client envoie `POST /api/preview`
- **THEN** la réponse SHALL être `400 Bad Request` avec `Content-Type: application/json` et un corps `{"errors": ["downscale: 10 hors bornes [64, 4096]"]}` (format inchangé par rapport au comportement actuel)

#### Scenario: Corps PNG directement utilisable par le navigateur
- **GIVEN** une réponse `200 OK` du serveur
- **WHEN** le client JS fait `const blob = await res.blob(); const url = URL.createObjectURL(blob); img.src = url;`
- **THEN** l'image SHALL s'afficher correctement dans le navigateur sans étape de décodage base64, ET les métadonnées SHALL être lisibles via `res.headers.get('X-Elapsed-Ms')` etc.
