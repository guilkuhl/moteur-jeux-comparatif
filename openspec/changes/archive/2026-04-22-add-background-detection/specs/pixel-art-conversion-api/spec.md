## ADDED Requirements

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
