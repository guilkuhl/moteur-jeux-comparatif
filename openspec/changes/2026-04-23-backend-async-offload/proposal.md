## Why

Sous FastAPI, un handler déclaré `def` (non-`async`) est exécuté dans le threadpool par défaut, mais un handler déclaré `async def` qui appelle du CPU-bound synchrone **bloque la boucle asyncio** et gèle toutes les autres requêtes concurrentes (preview live, masque de fond, SSE, catalogue). Le backend `pixel-lab/server_fastapi/` a plusieurs handlers qui cumulent les deux anti-patterns :

1. **`routers/preview.py:18` (`def api_preview`)** — synchrone, mais appelle `preview_runner.render` qui fait load PIL + downscale + boucle d'étapes OpenCV/NumPy. FastAPI l'exécute sur son threadpool (OK pour la boucle), mais **sans offload explicite**, donc aucune garantie d'élasticité : les 40 threads du pool par défaut sont saturables par un batch de previews, et le cache n'est pas consulté avant de prendre un slot.
2. **`routers/bgmask.py:18` (`def api_bgmask`)** — idem : I/O image + FFT numpy, dans le threadpool, sans dédup : deux requêtes identiques simultanées recalculent deux fois avant que la première populate le cache.
3. **`routers/cleanup.py:69, 96, 123` (`async def detect_duplicates`/`detect_subpixel`/`normalize`)** — **déclarées `async` mais exécutent du CPU-bound directement** (pHash O(n²), FFT phase correlate, crop/paste PIL). Conséquence : chaque appel fige la boucle asyncio pour 100 ms à plusieurs secondes selon la taille du spritesheet. Pendant ce temps, **aucun autre endpoint ne répond** — le live preview, le SSE d'un job en cours, et même `/api/capabilities` sont bloqués.

Le cache preview (`services/preview_cache.py`) et le cache bgmask (`services/bgmask_cache.py`) existent déjà et fonctionnent, mais **ils ne dédupent pas les requêtes en vol** : si deux clients (ou le même client après un hot-reload) demandent le même (image, pipeline) en parallèle, le calcul est fait deux fois, puis le résultat du second écrase celui du premier dans le cache.

Priorité : le point (3) est le plus urgent — les routes cleanup gèlent littéralement l'IHM le temps du calcul. Les points (1) et (2) sont des améliorations de robustesse sous charge et de dédup.

## What Changes

- **MODIFIED** `pixel-lab/server_fastapi/routers/cleanup.py` : les trois handlers `detect_duplicates`, `detect_subpixel`, `normalize` SHALL offloader leur section CPU-bound via `await asyncio.to_thread(...)`. Les sections I/O asynchrones (`await request.json()`) restent sur la boucle. L'emballage est une extraction locale de la partie calcul en fonction `_compute_*` passée à `asyncio.to_thread`.
- **MODIFIED** `pixel-lab/server_fastapi/routers/preview.py` : `api_preview` reste `def` (bonne forme FastAPI pour un handler purement CPU-bound), mais gagne une **consultation cache préalable** avant tout travail et une **dédup des requêtes en vol** via un dict `(key → asyncio.Future)` partagé. Si une requête identique est en vol, la seconde attend son résultat au lieu de recalculer.
- **MODIFIED** `pixel-lab/server_fastapi/routers/bgmask.py` : même traitement — `api_bgmask` reste `def`, mais ajoute la dédup en vol sur la clé de cache déjà calculée à la ligne 21. Le lookup cache existant reste inchangé.
- **MODIFIED** `pixel-lab/server_fastapi/services/preview_cache.py` : `max_size` passe de 32 à 128 pour couvrir des sessions multi-images × multi-pipelines sans éviction prématurée. Ajout d'un `InflightDedup` partagé (classe courte avec un `threading.Lock` + `dict[key, Future]`) exploitable par preview et bgmask.
- **NEW** `pixel-lab/server_fastapi/services/inflight.py` : petit module utilitaire exposant `InflightDedup.get_or_compute(key, factory)` qui renvoie le `Future` existant ou en crée un nouveau avec `factory()` exécuté dans un thread. Utilisable sync ou async.
- **PAS DE BREAKING CHANGE** sur les contrats API : aucun changement de payload, headers ou format de réponse. Les gains sont purement observables : (a) les endpoints cleanup ne figent plus la boucle asyncio, (b) deux requêtes preview/bgmask identiques concurrentes → un seul calcul, (c) cache preview plus généreux.

## Capabilities

### New Capabilities
_Aucune nouvelle capability._

### Modified Capabilities
- `pixel-art-conversion-api` : ajout de trois exigences — offload CPU des routes cleanup, dédup des requêtes preview/bgmask en vol, capacité du cache preview portée à 128 entrées.

## Impact

- **Code touché**
  - `pixel-lab/server_fastapi/routers/cleanup.py` : ~40 lignes (extraction de 3 blocs CPU en fonctions + `await asyncio.to_thread`).
  - `pixel-lab/server_fastapi/routers/preview.py` : ~15 lignes (wrap avec dédup).
  - `pixel-lab/server_fastapi/routers/bgmask.py` : ~15 lignes (wrap avec dédup).
  - `pixel-lab/server_fastapi/services/preview_cache.py` : 2 lignes (constante `max_size`).
  - `pixel-lab/server_fastapi/services/inflight.py` : nouveau fichier, ~40 lignes.
  - `pixel-lab/server_fastapi/tests/` : 1 test de non-régression par route modifiée (vérifier réponse identique + test de dédup).
- **APIs modifiées** : aucune. Payloads, headers, codes HTTP inchangés.
- **Dépendances** : aucune nouvelle (stdlib `asyncio`, `concurrent.futures`, `threading`).
- **Sécurité** : surface identique.
- **Performance** :
  - Cleanup : boucle asyncio non bloquée → latence p99 des autres endpoints revient du niveau "plusieurs secondes" à "quelques ms" sous charge concurrente.
  - Preview/bgmask : N requêtes identiques concurrentes → 1 calcul au lieu de N.
  - Cache preview : éviction 4× plus tardive.
- **Migration de données** : aucune.
- **Compatibilité descendante** : 100 %. Le front n'a aucun changement à faire.
- **Rollback** : `git revert` simple.
