# pixel-art-conversion-api Specification

## Purpose
TBD - created by archiving change add-live-preview. Update Purpose after archive.
## Requirements
### Requirement: La route POST /api/preview SHALL exécuter un pipeline en mémoire et renvoyer un PNG volatile
Le serveur MUST exposer `POST /api/preview` qui accepte un corps JSON `{image: <basename>, pipeline: [{algo, method, params}, ...], downscale: <int|null>}`, applique le pipeline sur l'image cible en mémoire via l'import direct des modules `pixel-lab/scripts/algorithms/*.py`. L'endpoint MUST NOT écrire sur disque, MUST NOT modifier `history.json`, MUST NOT créer de dossier dans `outputs/`.

Format de réponse : voir la requirement « La route POST /api/preview SHALL retourner un PNG binaire avec métadonnées en headers HTTP » (PNG binaire + headers `X-Width`, `X-Height`, `X-Elapsed-Ms`, `X-Cache-Hit-Depth`).

#### Scenario: Preview mono-étape réussi
- **GIVEN** un payload valide `{image:"sprite.png", pipeline:[{algo:"sharpen",method:"unsharp_mask",params:{radius:1.2,percent:200}}], downscale:256}`
- **WHEN** le client envoie `POST /api/preview`
- **THEN** la réponse SHALL être `200 OK` avec `Content-Type: image/png` et des headers `X-Width <= 256`, `X-Height <= 256`, `X-Elapsed-Ms`, `X-Cache-Hit-Depth`, et aucun fichier SHALL avoir été créé dans `outputs/sprite/` ou `history.json` SHALL rester strictement identique à son état avant la requête

#### Scenario: Preview pipeline multi-étapes
- **GIVEN** un payload `{image:"sprite.png", pipeline:[{algo:"denoise",method:"median",params:{size:3}},{algo:"sharpen",method:"unsharp_mask",params:{radius:1.0,percent:150}}], downscale:256}`
- **WHEN** le client envoie la requête
- **THEN** le serveur SHALL appliquer les deux étapes séquentiellement en mémoire, la sortie de l'étape 1 SHALL être l'entrée de l'étape 2, et la réponse SHALL contenir le PNG final (binaire) dans le corps

#### Scenario: Pas de persistance
- **GIVEN** un appel `POST /api/preview` réussi
- **WHEN** on inspecte `outputs/` et `history.json` immédiatement après
- **THEN** aucun nouveau fichier `iter_NNN_*.png` SHALL avoir été créé, et `history.json` SHALL être byte-à-byte identique à son contenu avant l'appel

### Requirement: La route POST /api/preview SHALL retourner un PNG binaire avec métadonnées en headers HTTP
Le serveur MUST renvoyer la réponse de `POST /api/preview` en tant que PNG binaire (`Content-Type: image/png`) dans le corps de la réponse, avec les métadonnées dans des headers HTTP personnalisés : `X-Width`, `X-Height`, `X-Elapsed-Ms`, `X-Cache-Hit-Depth`. L'encodage base64 et le wrapper JSON `{"png_base64": …}` MUST être supprimés. Les réponses d'erreur (400, 404, 409, 413, etc.) MUST continuer à utiliser le format JSON `{"errors": [...]}` ou `{"error": "..."}`.

#### Scenario: Réponse réussie au format binaire
- **GIVEN** un payload valide `{image:"sprite.png", pipeline:[{algo:"sharpen",method:"unsharp_mask",params:{radius:1.0,percent:150}}], downscale:256}`
- **WHEN** le client envoie `POST /api/preview`
- **THEN** la réponse SHALL être `200 OK` avec `Content-Type: image/png`, le corps SHALL être un PNG valide décodable par Pillow/navigateur, ET les headers SHALL inclure `X-Width`, `X-Height`, `X-Elapsed-Ms`, `X-Cache-Hit-Depth` avec des valeurs entières

#### Scenario: Header de cache hit
- **GIVEN** un premier appel `/api/preview` avec pipeline `[A, B]` puis un second avec pipeline `[A, B, C]` (préfixe identique)
- **WHEN** le serveur traite le second appel
- **THEN** la réponse `200 OK` SHALL contenir `X-Cache-Hit-Depth: 2`

#### Scenario: Erreur de validation reste en JSON
- **GIVEN** un payload avec `downscale: 10` (hors bornes [64, 4096])
- **WHEN** le client envoie `POST /api/preview`
- **THEN** la réponse SHALL être `400 Bad Request` avec `Content-Type: application/json` et un corps `{"errors": ["downscale: 10 hors bornes [64, 4096]"]}`

#### Scenario: Corps PNG directement utilisable par le navigateur
- **GIVEN** une réponse `200 OK` du serveur
- **WHEN** le client JS fait `const blob = await res.blob(); const url = URL.createObjectURL(blob); img.src = url;`
- **THEN** l'image SHALL s'afficher correctement sans étape de décodage base64, ET les métadonnées SHALL être lisibles via `res.headers.get('X-Elapsed-Ms')` etc.

### Requirement: Le preview SHALL appliquer un downscale par défaut et supporter un mode plein résolution
Le serveur MUST redimensionner l'image source à une longueur max de 256 pixels (en conservant le ratio) avant d'appliquer le pipeline, sauf si le payload contient explicitement `downscale: null`, auquel cas le pipeline SHALL être appliqué sur la taille originale. Le downscale MUST utiliser un resampling préservant la netteté pixel-art (`Image.Resampling.NEAREST` pour les images pixel-natives, ou `LANCZOS` pour les sources hautes résolutions — choix à documenter dans le code).

#### Scenario: Downscale par défaut
- **GIVEN** une image source `1024×1024` et un payload sans champ `downscale` (ou `downscale: 256`)
- **WHEN** le client envoie `POST /api/preview`
- **THEN** le serveur SHALL réduire l'image à `256×256` avant d'appliquer le pipeline, et la réponse SHALL contenir `"width": 256, "height": 256`

#### Scenario: Plein résolution explicite
- **GIVEN** une image source `1024×1024` et un payload `{..., "downscale": null}`
- **WHEN** le client envoie `POST /api/preview`
- **THEN** le serveur SHALL NOT redimensionner, le pipeline SHALL être appliqué sur `1024×1024`, et la réponse SHALL contenir `"width": 1024, "height": 1024`

#### Scenario: Downscale personnalisé
- **GIVEN** un payload `{..., "downscale": 512}`
- **WHEN** le client envoie la requête
- **THEN** le serveur SHALL réduire l'image source à 512 px de longueur max en conservant le ratio

### Requirement: Le serveur SHALL cacher les préfixes de pipeline pour éviter les recalculs lors de tweaks successifs
Pour chaque requête `POST /api/preview`, le serveur MUST vérifier dans un cache en mémoire (LRU, capacité min 32 entrées) si le préfixe du pipeline courant a déjà été calculé pour la même image source. La clé de cache MUST inclure : basename de l'image, `mtime` du fichier source, la valeur `downscale`, et la liste des étapes sous forme hashable `(algo, method, tuple_params)`. Si un préfixe est trouvé dans le cache, le serveur MUST partir de l'image cachée et n'exécuter que les étapes non encore cachées.

#### Scenario: Hit sur préfixe identique
- **GIVEN** un premier appel `/api/preview` avec pipeline `[A, B, C]` terminé avec succès
- **WHEN** un second appel arrive avec pipeline `[A, B, D]` (mêmes `A` et `B`, `D` nouveau)
- **THEN** le serveur SHALL récupérer le résultat de `[A, B]` depuis le cache sans recalculer, SHALL appliquer uniquement `D`, et la réponse SHALL refléter le pipeline complet `[A, B, D]`

#### Scenario: Invalidation par changement amont
- **GIVEN** un cache contenant `[A, B]` et `[A, B, C]`
- **WHEN** un nouvel appel arrive avec pipeline `[A', B, C]` (`A'` a des params différents de `A`)
- **THEN** le serveur SHALL NE PAS utiliser les entrées `[A, B]` ou `[A, B, C]` (la clé inclut l'étape `A`, donc le hash diffère), SHALL recalculer `[A']` puis `[A', B]` puis `[A', B, C]`, et éventuellement stocker ces nouveaux préfixes en cache

#### Scenario: Invalidation par mtime de l'image source
- **GIVEN** un cache contenant un préfixe pour `sprite.png` au mtime T1
- **WHEN** l'utilisateur édite `sprite.png` (mtime T2 > T1) puis déclenche un preview avec le même pipeline
- **THEN** le serveur SHALL considérer la clé différente (car mtime inclus) et SHALL recalculer depuis l'image source actualisée

### Requirement: La validation de POST /api/preview SHALL réutiliser les règles de /api/convert
Le serveur MUST valider le payload de `POST /api/preview` avec les mêmes règles que `POST /api/convert` :
- L'algo MUST appartenir à l'allow-list `{sharpen, scale2x, denoise, pixelsnap}`.
- La méthode MUST exister dans `METHODS` du module ciblé.
- Chaque param MUST exister dans `PARAMS[<method>]` et respecter son type et ses bornes.
- Le nom d'image MUST être un basename pur (sans `..`, sans `/`, sans `\`) et le fichier MUST exister dans `inputs/`.
- Si `downscale` est fourni, il MUST être un entier entre 64 et 4096 inclus, ou `null`.

En cas d'erreur, la réponse MUST être `400 Bad Request` avec un JSON `{"errors": [<messages>]}` (même format que `/api/convert`).

#### Scenario: Algo inconnu rejeté
- **GIVEN** un payload avec `pipeline:[{algo:"rm_rf", method:"root"}]`
- **WHEN** le serveur valide la requête
- **THEN** la réponse SHALL être `400` avec un message identifiant l'algo fautif, et aucun import / exécution SHALL avoir lieu

#### Scenario: Downscale hors bornes
- **GIVEN** un payload `{..., "downscale": 10}` (< 64)
- **WHEN** le serveur valide la requête
- **THEN** la réponse SHALL être `400` avec un message indiquant que `downscale` doit être entre 64 et 4096 ou null

### Requirement: L'endpoint /api/preview SHALL ne pas interférer avec un job /api/convert en cours
Le lock global `_active_job` utilisé par `/api/convert` MUST NE PAS être acquis par `/api/preview`. Un preview SHALL pouvoir s'exécuter même si un job de conversion est actif, et vice versa : un clic sur `[▶ Lancer]` SHALL être recevable à tout moment (sous réserve des contraintes propres de `/api/convert`), indépendamment des previews en cours.

#### Scenario: Preview pendant un job de conversion actif
- **GIVEN** un job `/api/convert` en cours depuis 10 secondes sur l'image `sprite.png`
- **WHEN** le client envoie `POST /api/preview` sur `sprite.png` avec un pipeline différent
- **THEN** la requête preview SHALL être acceptée et traitée indépendamment, la réponse `200 OK` SHALL être renvoyée sans attendre la fin du job de conversion, et les événements SSE du job en cours SHALL continuer à être diffusés normalement

#### Scenario: Convert acceptable pendant une rafale de previews
- **GIVEN** l'utilisateur qui enchaîne des previews
- **WHEN** il clique sur `[▶ Lancer]` sans attendre la fin du dernier preview
- **THEN** `POST /api/convert` SHALL répondre `202 Accepted` avec un `job_id` si aucun job n'est actif (les previews en cours ne bloquent pas), ou `409 Conflict` si un autre job est déjà actif

### Requirement: La route `GET /api/bgmask` SHALL retourner le masque de fond détecté pour une image source, en PNG

Le serveur MUST exposer `GET /api/bgmask?image=<basename>&tolerance=<int>&feather=<int>` qui :

- Valide `image` comme basename pur (pas de `..`, `/`, `\`) et vérifie son existence dans `inputs/`.
- Valide `tolerance` ∈ [0, 50] (défaut 8 si absent).
- Valide `feather` ∈ [0, 5] (défaut 0 si absent).
- Charge l'image, appelle `bgdetect.compute_bg_mask(img, tolerance=tolerance, feather=feather)`.
- Retourne un PNG RGBA `image/png` où :
  - `alpha == 0` pour les pixels de fond (masque `False`)
  - `alpha == 255` pour les pixels foreground (masque `True`)
  - Le canal RGB contient la couleur de fond détectée (`detect_bg_color`) partout, ou noir si `None`
- Utilise un cache mémoire LRU (capacité ≥ 16) avec clé `(basename, mtime_ns, tolerance, feather)`.

En cas d'erreur de validation, la réponse SHALL être `400 Bad Request` avec `{"errors": [...]}`. En cas d'image introuvable, `404 Not Found`.

Cet endpoint MUST NE PAS acquérir le lock `_active_job` utilisé par `/api/convert`.

#### Scenario: Masque retourné pour une image au fond uni

- **GIVEN** une image `sprite.png` avec fond uni `#404040`
- **WHEN** le client envoie `GET /api/bgmask?image=sprite.png`
- **THEN** la réponse SHALL être `200 OK` avec `Content-Type: image/png`, les dimensions SHALL être identiques à celles de `sprite.png`, et les pixels de fond SHALL avoir `alpha == 0` tandis que ceux du sprite SHALL avoir `alpha == 255`

#### Scenario: Fond non détecté

- **GIVEN** une image dont les 4 coins sont tous différents
- **WHEN** le client envoie `GET /api/bgmask?image=<ce fichier>`
- **THEN** la réponse SHALL être `200 OK` avec un PNG entièrement `alpha == 255` (aucun fond détecté = tout est foreground), ou optionnellement un header `X-Bgmask-Status: no-bg-detected` pour signalement côté client

#### Scenario: Cache hit sur mtime inchangé

- **GIVEN** un premier appel `/api/bgmask?image=x.png&tolerance=8` réussi
- **WHEN** un second appel identique arrive dans la même session (mtime inchangé)
- **THEN** le serveur SHALL répondre depuis le cache sans relire le fichier source ni relancer le flood-fill (vérifiable via log ou header `X-Cache: HIT`)

#### Scenario: Invalidation par mtime

- **GIVEN** un cache contenant le masque pour `sprite.png` au mtime T1
- **WHEN** l'utilisateur édite `sprite.png` (nouveau mtime T2) puis appelle `/api/bgmask?image=sprite.png`
- **THEN** le serveur SHALL recalculer le masque (cache miss par clé)

#### Scenario: Paramètres hors bornes

- **GIVEN** un appel `GET /api/bgmask?image=x.png&tolerance=100`
- **WHEN** le serveur valide la requête
- **THEN** la réponse SHALL être `400 Bad Request` avec un message indiquant la borne max `50` pour `tolerance`

### Requirement: Les payloads `/api/convert` et `/api/preview` SHALL accepter et valider le paramètre `preserve_bg` dans chaque étape du pipeline

Les validateurs de `POST /api/convert` et `POST /api/preview` MUST accepter `preserve_bg: bool` dans les `params` de chaque étape, pour les algos qui le déclarent dans leur `PARAMS` (à savoir `denoise` et `sharpen` après cette spec).

Si `preserve_bg` est fourni pour un algo qui ne le déclare pas (ex. `scale2x`, `pixelsnap`), la réponse SHALL être `400 Bad Request` avec message explicite.

Si `preserve_bg` est un type non booléen (ex. string, int), la réponse SHALL être `400 Bad Request`.

#### Scenario: preserve_bg valide passe la validation

- **GIVEN** un payload `/api/convert` avec `pipeline:[{algo:"sharpen", method:"unsharp_mask", params:{radius:1, percent:150, preserve_bg:true}}]`
- **WHEN** le serveur valide la requête
- **THEN** la validation SHALL passer et le job SHALL être lancé normalement

#### Scenario: preserve_bg sur un algo incompatible rejeté

- **GIVEN** un payload avec `pipeline:[{algo:"scale2x", method:"nearest", params:{scale:2, preserve_bg:true}}]`
- **WHEN** le serveur valide la requête
- **THEN** la réponse SHALL être `400 Bad Request` avec message « preserve_bg non supporté pour scale2x/nearest »

### Requirement: Le cache du masque de fond SHALL être partagé entre `/api/bgmask`, `/api/preview` et `/api/convert`

Un cache mémoire unique (`OrderedDict` ou équivalent LRU avec capacité ≥ 16) keyé par `(basename, mtime_ns, tolerance, feather)` MUST être utilisé par :

- `/api/bgmask` pour retourner directement le masque.
- L'application de `preserve_bg=True` à une étape de `/api/preview` (via l'import direct des algos).
- L'application de `preserve_bg=True` à une étape de `/api/convert` (via `process.py` en subprocess ne bénéficie pas du cache in-memory ; le cache est alors recalculé une fois par job. V1 accepte cette limitation).

#### Scenario: Réutilisation du masque entre bgmask et preview

- **GIVEN** un appel `/api/bgmask?image=x.png&tolerance=8` qui peuple le cache
- **WHEN** un appel `/api/preview` suivant traite la même image avec `preserve_bg=true` sur une étape (avec tolerance par défaut 8)
- **THEN** le calcul du masque dans le traitement de l'étape SHALL être un cache hit (mesurable par timing < 2 ms pour l'étape masque)

### Requirement: Le backend SHALL être un serveur Flask local lié strictement à 127.0.0.1
Le backend MUST être implémenté avec Flask dans `pixel-lab/server/app.py`, démarré sur `127.0.0.1` (jamais `0.0.0.0`) et écouter par défaut sur le port 5500. Il importe directement les modules `pixel-lab/scripts/algorithms/*.py` via le module partagé `pixel-lab/scripts/apply_step.py` — toutes les étapes de pipeline s'exécutent in-process (plus de spawn subprocess pour `/api/convert`).

#### Scenario: Bind localhost strict
- **GIVEN** le serveur Flask démarré
- **WHEN** on inspecte la socket d'écoute
- **THEN** elle SHALL être liée à `127.0.0.1:<port>` exclusivement, et toute requête depuis une autre machine SHALL recevoir une erreur de connexion réseau

#### Scenario: Exécution in-process partagée avec le preview
- **GIVEN** le fichier `server/app.py`
- **WHEN** on lit ses imports
- **THEN** il SHALL importer `run_step` depuis `apply_step.py` et utiliser les modules `algorithms/*.py` via ce module partagé ; il SHALL NOT lancer `subprocess.Popen` pour invoquer `scripts/process.py` depuis `/api/convert`

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

#### Scenario: Warning scale2x au milieu
- **GIVEN** un pipeline `[denoise, scale2x, sharpen]` (scale2x change la résolution)
- **WHEN** le job s'exécute
- **THEN** un événement SSE `{type:"warning", message:"scale2x au milieu d'un pipeline, …"}` SHALL être diffusé avant le `step_start` de l'étape `scale2x`, mais le pipeline SHALL continuer normalement

