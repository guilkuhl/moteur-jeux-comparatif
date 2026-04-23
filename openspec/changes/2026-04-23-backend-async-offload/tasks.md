## 1. Module `services/inflight.py`

- [x] 1.1 Créer `pixel-lab/server_fastapi/services/inflight.py` avec la classe `InflightDedup[T]` conforme au design (§ Decision 3) : méthode `async def run(self, key: tuple, factory: Callable[[], T]) -> T`, `_lock: threading.Lock`, `_inflight: dict[tuple, asyncio.Future[T]]`, purge dans `finally`.
- [x] 1.2 Ajouter dans `pixel-lab/server_fastapi/tests/` un fichier `test_inflight.py` avec trois cas : (a) appel unique retourne `factory()` ; (b) deux appels concurrents avec même clé → `factory` appelée **une seule fois**, les deux reçoivent le même résultat (vérifier via un compteur `calls += 1` dans la factory) ; (c) exception dans `factory` propagée aux deux appelants puis purge de la clé (un 3ᵉ appel re-appelle `factory`).

## 2. Offload CPU dans `routers/cleanup.py`

- [x] 2.1 Extraire le corps calcul de `detect_duplicates` (lignes 75-92 actuelles : `iter_cells`, `_phash`, double boucle hamming) dans une fonction privée sync `_compute_duplicates(image_name: str, threshold: int) -> dict` au même module.
- [x] 2.2 Réécrire `detect_duplicates` pour valider le payload (image_name, threshold) puis `return await asyncio.to_thread(_compute_duplicates, image_name, threshold)`. Garder le `HTTPException(400)` avant le `to_thread`.
- [x] 2.3 Idem pour `detect_subpixel` : extraire dans `_compute_subpixel(image_name: str) -> dict` (lignes 101-119 actuelles, incluant la boucle `_phase_correlate`).
- [x] 2.4 Idem pour `normalize` : extraire dans `_compute_normalize(image_name: str, alignment: str) -> dict` (lignes 129-170 actuelles, incluant l'écriture du fichier et `history_store.update`).
- [x] 2.5 Ajouter `import asyncio` en tête de fichier si absent.
- [x] 2.6 Test de non-régression : ajouter un fichier `tests/test_cleanup_async.py` qui lance en parallèle via `asyncio.gather` un appel `detect_duplicates` et un appel à un endpoint rapide (ex. `GET /api/capabilities`) — le second SHALL répondre en <50 ms même pendant que le premier calcule. Utiliser un spritesheet de test déjà présent dans `tests/fixtures/` (ou en créer un minimal).

## 3. Dédup en vol dans `routers/preview.py`

- [x] 3.1 Instancier `_preview_dedup = InflightDedup()` au niveau module.
- [x] 3.2 Passer `api_preview` de `def` à `async def`.
- [x] 3.3 Construire une clé de dédup stable : `(payload.image, payload.downscale, tuple((s.algo, s.method, tuple(sorted((s.params or {}).items()))) for s in payload.pipeline), payload.use_gpu)`. Extraire ce build dans une fonction `_dedup_key(payload: PreviewRequest) -> tuple`.
- [x] 3.4 Remplacer l'appel direct à `preview_runner.render(...)` par `png_bytes, width, height, hit_depth = await _preview_dedup.run(key, lambda: preview_runner.render(...))`. Vérifier que les arguments capturés dans la lambda sont bien ceux de la requête (pas de late binding sur variable mutable).
- [x] 3.5 Le calcul `elapsed_ms` reste inchangé (mesure le temps perçu par l'appelant, dédup incluse — c'est bien ce qu'on veut pour les métriques utilisateur).
- [x] 3.6 Test de dédup : dans `tests/test_preview_dedup.py`, lancer `asyncio.gather` de deux appels `POST /api/preview` identiques. Vérifier via un patch/spy sur `preview_runner.render` que la fonction est appelée **une seule fois**. Les deux réponses MUST avoir le même corps PNG (octet-à-octet).

## 4. Dédup en vol dans `routers/bgmask.py`

- [x] 4.1 Instancier `_bgmask_dedup = InflightDedup()` au niveau module.
- [x] 4.2 Passer `api_bgmask` de `def` à `async def`.
- [x] 4.3 Conserver le lookup cache existant (ligne 23-35). Après un cache miss, remplacer le bloc calcul (lignes 37-56) par `png_bytes, bg_color = await _bgmask_dedup.run(key, lambda: _compute_bgmask(path, query))` où `_compute_bgmask(path: Path, query: BgmaskQuery) -> tuple[bytes, tuple|None]` encapsule les lignes 37-55 (détection, construction RGBA, encodage PNG) et **ne touche pas au cache** (le cache `put` reste dans le handler, après le dedup).
- [x] 4.4 Extraire `_compute_bgmask` en fonction de module (même fichier).
- [x] 4.5 Test de dédup : dans `tests/test_bgmask_dedup.py`, lancer `asyncio.gather` de deux `GET /api/bgmask?image=...` identiques sur un cache vide. Vérifier qu'un spy sur `bgdetect.detect_bg_color` n'est appelé qu'une fois.

## 5. Capacité du cache preview

- [x] 5.1 Dans `pixel-lab/server_fastapi/services/preview_cache.py` ligne 50, changer `PreviewCache(max_size=32)` en `PreviewCache(max_size=128)`.
- [x] 5.2 Ajuster `__init__` signature ligne 12 pour garder le default à 32 (les tests unitaires du cache n'en dépendent pas, mais on reste conservateur sur le default constructeur ; seul l'instance partagée passe à 128).

## 6. Vérification et commit

- [x] 6.1 Lancer `ruff` et `mypy`/`pyright` (selon `pyproject.toml`) sur `pixel-lab/server_fastapi/` : zéro warning/erreur introduite.
- [x] 6.2 Lancer la suite pytest complète : `cd pixel-lab && pytest server_fastapi/tests/ -q`. Zéro régression.
- [ ] 6.3 Test manuel : lancer le serveur (`python pixel-lab/serve.py` ou équivalent), ouvrir le frontend, activer live preview, tweaker des params pendant qu'un `/api/cleanup/detect-duplicates` tourne sur un gros spritesheet → le preview SHALL continuer à répondre (avant le fix : il gèle jusqu'à la fin de cleanup).
- [ ] 6.4 Commit avec message clair décrivant l'offload CPU + dédup en vol. Push sur `claude/improve-performance-ui-l8Ldl`.
