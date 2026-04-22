## ADDED Requirements

### Requirement: La route POST /api/preview SHALL exécuter un pipeline en mémoire et renvoyer un PNG volatile
Le serveur MUST exposer `POST /api/preview` qui accepte un corps JSON `{image: <basename>, pipeline: [{algo, method, params}, ...], downscale: <int|null>}`, applique le pipeline sur l'image cible en mémoire via l'import direct des modules `pixel-lab/scripts/algorithms/*.py`, et renvoie une réponse synchrone `200 OK` contenant `{"png_base64": "<data>", "width": <int>, "height": <int>, "elapsed_ms": <int>}`. L'endpoint MUST NOT écrire sur disque, MUST NOT modifier `history.json`, MUST NOT créer de dossier dans `outputs/`.

#### Scenario: Preview mono-étape réussi
- **GIVEN** un payload valide `{image:"sprite.png", pipeline:[{algo:"sharpen",method:"unsharp_mask",params:{radius:1.2,percent:200}}], downscale:256}`
- **WHEN** le client envoie `POST /api/preview`
- **THEN** la réponse SHALL être `200 OK` avec `{"png_base64": "<non-empty>", "width": <int ≤ 256>, "height": <int ≤ 256>, "elapsed_ms": <int>}`, et aucun fichier SHALL avoir été créé dans `outputs/sprite/` ou `history.json` SHALL rester strictement identique à son état avant la requête

#### Scenario: Preview pipeline multi-étapes
- **GIVEN** un payload `{image:"sprite.png", pipeline:[{algo:"denoise",method:"median",params:{size:3}},{algo:"sharpen",method:"unsharp_mask",params:{radius:1.0,percent:150}}], downscale:256}`
- **WHEN** le client envoie la requête
- **THEN** le serveur SHALL appliquer les deux étapes séquentiellement en mémoire, la sortie de l'étape 1 SHALL être l'entrée de l'étape 2, et la réponse SHALL contenir le PNG final encodé en base64

#### Scenario: Pas de persistance
- **GIVEN** un appel `POST /api/preview` réussi
- **WHEN** on inspecte `outputs/` et `history.json` immédiatement après
- **THEN** aucun nouveau fichier `iter_NNN_*.png` SHALL avoir été créé, et `history.json` SHALL être byte-à-byte identique à son contenu avant l'appel

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
