## ADDED Requirements

### Requirement: Les routes /api/cleanup/* SHALL offloader leur calcul CPU hors de la boucle asyncio
Les handlers `POST /api/cleanup/detect-duplicates`, `POST /api/cleanup/detect-subpixel` et `POST /api/cleanup/normalize`, déclarés `async def` pour pouvoir lire le corps JSON via `await request.json()`, MUST exécuter toute section CPU-bound (itération pixels, pHash, FFT phase correlate, crop/paste PIL, écriture fichier) via `await asyncio.to_thread(_compute_*, ...)`. Aucun appel synchrone à `iter_cells`, `_phash`, `_phase_correlate`, `Image.crop`, `Image.paste` ou `Image.save` SHALL avoir lieu directement sur la boucle asyncio pendant la vie d'une requête. La validation des paramètres (image_name safe_name, bornes numériques) MUST rester avant l'offload afin qu'une requête invalide échoue sans coût de thread.

#### Scenario: detect-duplicates n'interfère pas avec un autre endpoint
- **GIVEN** un spritesheet de 100 cellules 64×64 déjà slicé, déclenchant un `detect_duplicates` mesurable à ≥ 500 ms
- **WHEN** un client lance `POST /api/cleanup/detect-duplicates` et, 50 ms plus tard, un second client lance `GET /api/capabilities`
- **THEN** le second appel SHALL recevoir sa réponse en moins de 100 ms, sans attendre la fin de `detect_duplicates`, ET le premier appel SHALL renvoyer son JSON `{pairs, threshold}` habituel sans changement de contrat

#### Scenario: detect-subpixel ne bloque pas le live preview
- **GIVEN** un spritesheet déjà slicé et un live preview actif sur une autre image
- **WHEN** un client lance `POST /api/cleanup/detect-subpixel` pendant qu'un slider de pipeline déclenche `POST /api/preview`
- **THEN** le `POST /api/preview` SHALL recevoir sa réponse PNG dans sa latence habituelle (≤ 500 ms pour un preview downscalé 256 px), indépendamment de la durée de `detect_subpixel`

#### Scenario: normalize valide les inputs avant de prendre un thread
- **GIVEN** un payload `normalize` avec `image: "../etc/passwd"` (échec `safe_name`)
- **WHEN** le client envoie `POST /api/cleanup/normalize`
- **THEN** le serveur SHALL répondre `400 bad_image` sans avoir soumis la moindre tâche à `asyncio.to_thread`

#### Scenario: erreur dans le thread propagée au client
- **GIVEN** un spritesheet valide mais dont le fichier est corrompu (PIL raise pendant `iter_cells`)
- **WHEN** `detect_duplicates` tourne dans le thread offloadé et raise une exception
- **THEN** FastAPI SHALL convertir l'exception en `500 Internal Server Error` (ou `HTTPException` si explicitement raised), ET la boucle asyncio SHALL rester saine pour les requêtes suivantes

### Requirement: /api/preview et /api/bgmask SHALL dédupliquer les requêtes identiques en vol
Le serveur MUST partager le résultat d'un calcul en cours entre deux requêtes identiques concurrentes via un `InflightDedup` par route. La clé de dédup `/api/preview` MUST inclure `(payload.image, payload.downscale, pipeline_tuple_stable, payload.use_gpu)` où `pipeline_tuple_stable` est le tuple `(algo, method, tuple(sorted((params or {}).items())))` pour chaque étape. La clé de dédup `/api/bgmask` MUST réutiliser la clé de cache existante `(image, mtime_ns, tolerance, feather, mode)`. Si deux clients lancent la même requête en parallèle, un seul calcul SHALL être exécuté ; les deux clients reçoivent la même réponse (corps identique octet-à-octet). En cas d'exception dans le calcul, tous les appelants concurrents SHALL recevoir la même exception, ET l'entrée dédup SHALL être purgée pour permettre une relance propre.

#### Scenario: deux previews identiques concurrents
- **GIVEN** une image `sprite.png` et un pipeline `[{algo:"sharpen", method:"unsharp_mask", params:{radius:1.0, percent:150}}]`
- **WHEN** deux clients lancent `POST /api/preview` avec ce payload **simultanément** (cache preview vide)
- **THEN** `preview_runner.render` SHALL être invoqué exactement une fois (vérifiable via spy), ET les deux clients SHALL recevoir la même réponse 200 avec PNG identique octet-à-octet et les mêmes headers `X-Width`, `X-Height`, `X-Cache-Hit-Depth`

#### Scenario: deux bgmask identiques concurrents
- **GIVEN** une image source `sprite.png` et une query `?tolerance=10&feather=2&mode=overlay` (cache bgmask vide)
- **WHEN** deux clients lancent `GET /api/bgmask` avec la même query **simultanément**
- **THEN** `bgdetect.detect_bg_color` SHALL être invoqué exactement une fois, ET les deux réponses SHALL porter `X-Cache: MISS` (la première ayant déclenché le calcul) ou l'une `MISS` et la seconde `HIT` selon l'ordonnancement, mais jamais deux `MISS` ayant chacune fait tourner `detect_bg_color` indépendamment

#### Scenario: requête isolée inchangée
- **GIVEN** une requête `POST /api/preview` sans concurrent
- **WHEN** le client envoie la requête
- **THEN** le comportement, les headers et le corps SHALL être strictement identiques au comportement antérieur (pas de régression sur le chemin chaud mono-client)

#### Scenario: exception partagée puis purge
- **GIVEN** une requête `POST /api/preview` avec un pipeline invalide qui fait raiser `preview_runner.render`
- **WHEN** deux clients envoient ce payload simultanément
- **THEN** les deux SHALL recevoir la même erreur (500 ou 400 selon le type d'exception), ET une 3ᵉ requête identique lancée **après** SHALL ré-exécuter `preview_runner.render` (la clé a été purgée du dédup)

### Requirement: Le cache LRU de /api/preview SHALL accepter au moins 128 entrées
L'instance partagée `preview_cache` exposée par `pixel-lab/server_fastapi/services/preview_cache.py` MUST être configurée avec `max_size=128` afin qu'une session de travail réaliste (4 images × 5 étapes × 3 previews par étape ≈ 60 entrées) ne provoque pas d'éviction prématurée. Le constructeur `PreviewCache(max_size: int = 32)` conserve son défaut pour les tests unitaires du cache qui instancient leur propre instance.

#### Scenario: 100 entrées stockées sans éviction
- **GIVEN** un cache preview fraîchement initialisé via l'instance partagée
- **WHEN** 100 clés distinctes sont insérées via `preview_cache.put(key_i, img)`
- **THEN** les 100 entrées SHALL être récupérables via `preview_cache.get(key_i)` (aucun `None` retourné)

#### Scenario: éviction LRU à 129ᵉ entrée
- **GIVEN** un cache preview avec 128 entrées
- **WHEN** une 129ᵉ clé est insérée
- **THEN** l'entrée la moins récemment utilisée SHALL être évincée (retourne `None` au prochain `get`), ET les 128 plus récentes SHALL rester accessibles
