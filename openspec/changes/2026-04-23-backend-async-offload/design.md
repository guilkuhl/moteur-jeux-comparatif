## Context

FastAPI utilise `anyio`/`starlette` pour dispatcher les handlers. Règle clé :

| Déclaration | Comportement |
|---|---|
| `def handler(...)` | Exécuté dans un threadpool (taille par défaut ≈ 40). La boucle asyncio reste libre. |
| `async def handler(...)` | Exécuté **directement sur la boucle asyncio**. Tout appel CPU-bound synchrone fige la boucle. |

Aujourd'hui, `cleanup.py` mélange les deux : `async def` pour pouvoir `await request.json()`, mais enchaîne ensuite des boucles numpy/FFT/PIL sans `await`. C'est le pire des cas — le développeur a probablement ajouté `async` par mimétisme, pensant que ça aide.

Le fix n'est pas de repasser en `def` (on perdrait `await request.json()`), mais d'extraire la section CPU et de la passer à `asyncio.to_thread(...)`. Trois lignes de refactor par handler.

Pour preview/bgmask, qui sont déjà `def`, le problème est différent : FastAPI gère bien le threadpool, mais deux requêtes identiques ne coopèrent pas. On ajoute une dédup en vol — classique dict `key → Future` avec lock.

## Goals / Non-Goals

**Goals**
- Aucune route ne gèle jamais la boucle asyncio plus de ~10 ms.
- Deux requêtes identiques en vol partagent le résultat.
- Aucun changement d'API externe.

**Non-Goals**
- Pas de rewrite des algorithmes (pHash O(n²) reste O(n²)).
- Pas de `ProcessPoolExecutor` ici — tout reste dans le même process. Le GIL est libéré par numpy/PIL sur les opérations lourdes, donc un threadpool suffit.
- Pas de persistance de cache disque.

## Decisions

### Decision 1 — `asyncio.to_thread` plutôt qu'un `ThreadPoolExecutor` dédié

`asyncio.to_thread` (Python 3.9+) soumet à l'executor par défaut de la boucle, partagé avec FastAPI. C'est exactement ce qu'on veut : pas de pool à dimensionner, pas de fuite si la boucle est arrêtée, taille configurable via `anyio.to_thread.current_default_thread_limiter().total_tokens = N` si besoin plus tard.

**Alternative rejetée** : `concurrent.futures.ThreadPoolExecutor` dédié au module cleanup. Rejetée car double la complexité de cleanup (lifecycle) sans gain mesurable — le threadpool anyio partage déjà la capacité entre tous les handlers `def` et les `asyncio.to_thread`.

### Decision 2 — Forme de l'extraction CPU

Pour chaque handler cleanup, on extrait la section calcul dans une fonction privée `_compute_*` **sync**. Le handler `async def` devient :

```python
@router.post("/detect-duplicates")
async def detect_duplicates(request: Request) -> dict:
    payload = await request.json()
    image_name = payload.get("image")
    threshold = int(payload.get("similarity_threshold", 5))
    if not image_name or not safe_name(image_name):
        raise HTTPException(status_code=400, detail="bad_image")
    return await asyncio.to_thread(_compute_duplicates, image_name, threshold)
```

et `_compute_duplicates(image_name: str, threshold: int) -> dict` contient l'appel à `iter_cells`, le pHash et la double boucle. La validation reste **avant** le `to_thread` (on n'offload pas du travail qui peut raiser 400).

### Decision 3 — API du module `inflight`

```python
# services/inflight.py
from __future__ import annotations
import asyncio
import threading
from collections.abc import Callable
from typing import TypeVar, Generic

T = TypeVar("T")

class InflightDedup(Generic[T]):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._inflight: dict[tuple, asyncio.Future[T]] = {}

    async def run(self, key: tuple, factory: Callable[[], T]) -> T:
        loop = asyncio.get_running_loop()
        with self._lock:
            fut = self._inflight.get(key)
            if fut is None:
                fut = loop.create_future()
                self._inflight[key] = fut
                owner = True
            else:
                owner = False
        if owner:
            try:
                result = await asyncio.to_thread(factory)
                fut.set_result(result)
            except Exception as e:  # noqa: BLE001
                fut.set_exception(e)
            finally:
                with self._lock:
                    self._inflight.pop(key, None)
        return await fut
```

**Contrat** : le premier appelant pour une clé exécute `factory()` dans un thread et publie le résultat ; les appelants suivants attendent le même Future. En cas d'exception, tous les appelants la reçoivent. Le dict est purgé dans `finally` donc pas de fuite.

**Note subtile** : `loop.create_future()` doit être créé dans le loop de l'appelant — c'est OK tant que le premier appelant fixe le loop pour la vie du Future. En pratique FastAPI tourne sur un seul loop, donc tous les appelants partagent le même.

**Alternative rejetée** : `asyncio.Lock` par clé. Rejetée car on veut partager le **résultat**, pas juste sérialiser. Une Lock forcerait le second appelant à re-consulter le cache après le déblocage, avec une fenêtre de race si le cache a une TTL.

### Decision 4 — Intégration dans preview/bgmask

Pour preview :

```python
_dedup: InflightDedup[tuple[bytes, int, int, int]] = InflightDedup()

def api_preview(payload: PreviewRequest) -> Response:
    t0 = time.perf_counter()
    key = _make_dedup_key(payload)  # (image, mtime_ns, downscale, pipeline_tuple, use_gpu)
    png_bytes, width, height, hit_depth = _run_dedup_sync(key, lambda: preview_runner.render(...))
    ...
```

Sauf que `api_preview` est `def`, pas `async def`. On a deux options :

- **Option A** : basculer `api_preview` en `async def` pour pouvoir `await dedup.run(...)`. FastAPI l'exécute alors sur la boucle, mais comme la factory `render` est offloadée via `to_thread`, la boucle reste libre.
- **Option B** : garder `def` et utiliser un dédup synchrone (dict + `threading.Event`). Plus simple conceptuellement, mais on perd la cohérence avec cleanup.

**Choix : Option A**. Raison : sous FastAPI, un `async def` avec `await asyncio.to_thread` a exactement le même profil perf qu'un `def` pur, mais permet de composer avec la dédup async. On uniformise.

### Decision 5 — `max_size` du cache preview : 32 → 128

Arbitraire mais motivé : un utilisateur qui tweake 3 params sur un pipeline de 5 étapes, sur 4 images différentes, génère déjà 3×5×4 = 60 entrées de préfixe. 32 évince avant que le workflow se termine. 128 ≈ 4× ça, soit ~2 MB RAM max (preview downscalé à 256 px = ~260 KB PNG → ~130 KB PIL → ×128 = ~16 MB en pic, acceptable). On ne va pas jusqu'à 512 pour éviter la consommation mémoire sur sessions très longues.

## Risks / Trade-offs

- **Risque** : un bug dans `InflightDedup` pourrait hang une requête indéfiniment si le `finally` est contourné. Mitigation : tests unitaires (cas succès, cas exception, cas deux requêtes identiques concurrentes).
- **Trade-off** : la dédup ajoute une indirection pour 0 gain sur les requêtes isolées. Mesurable en microbench (<50 µs). Négligeable vs. le coût d'un preview (50–500 ms).
- **Risque** : `asyncio.to_thread` peut saturer le threadpool si un pipeline très long bloque tous les threads. Atténuation : FastAPI dimensionne le pool à ~40 ; un cleanup typique prend <2 s ; saturation improbable en usage local.

## Migration Plan

Pas de migration. Les tests de non-régression garantissent que :
1. Les réponses sont identiques octet-à-octet pour les mêmes inputs.
2. La dédup est transparente pour un client unique.
3. La dédup fonctionne pour deux clients simultanés (test avec `asyncio.gather` de deux appels identiques).

## Open Questions

Aucune.
