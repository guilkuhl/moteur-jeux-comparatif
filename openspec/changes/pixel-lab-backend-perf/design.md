## Context

Le Pixel Lab a aujourd'hui deux chemins d'exécution pour les algorithmes :

- **Chemin CLI / Convert officiel** : `scripts/process.py` est un script autonome qui charge une image, applique un algo, sauvegarde `iter_NNN_*.png` et met à jour `history.json`. Il est appelé par `workflow.py`, `batch.py`, et par `_run_job` dans le serveur via `subprocess.Popen`. Le choix du subprocess a été pris dans le change `add-dashboard-conversion` pour **éviter le drift** entre le chemin CLI et le chemin dashboard (décision D2 à l'époque).
- **Chemin Live Preview** : `/api/preview` (ajouté par `add-live-preview`) importe directement les modules `algorithms/*.py` via `_apply_step` (`app.py:454`) et garde le résultat en mémoire. La décision D9 de ce change note explicitement que D2 ne s'appliquait qu'aux artefacts écrits — or le preview n'en écrit aucun, donc l'import direct est sans risque.

La situation actuelle a un coût inutile : le chemin Convert relance un interpréteur Python à chaque étape × chaque image, alors qu'on dispose déjà d'une implémentation in-process éprouvée côté preview. L'écart est mesurable : 100–300 ms de spawn + réimport Pillow/NumPy par étape, vs < 10 ms d'appel de fonction pour le même travail utile. Le cache `/api/preview` atteint des temps de `cache_hit_depth=N` à **9 ms** vs **97 ms** (`add-live-preview/tasks.md` §10.3) — c'est un ordre de grandeur.

Le change vise à unifier les deux chemins autour d'une seule fonction `run_step(img, algo, method, params) → (Image, metadata)`, utilisée par `process.py` (CLI), `_run_job` (Convert dashboard) et `/api/preview` (live). La logique de **nommage des iter** et de **mise à jour de `history.json`** reste côté orchestrateur (pas mutualisée avec le preview qui n'écrit rien), mais factorisée dans des helpers partagés pour éviter la divergence.

En parallèle, deux optimisations plus petites sont embarquées : (a) suppression du transport base64 sur `/api/preview` (le format binaire direct est déjà utilisé par `/api/bgmask`, c'est un choix cohérent), et (b) préparation d'une entrée serveur production (gunicorn) sans retirer le fallback `app.run`.

## Goals / Non-Goals

**Goals:**
- Éliminer le spawn subprocess dans `_run_job` : tous les algos s'exécutent dans le process Flask, via les mêmes modules `algorithms/*.py` que le preview.
- Conserver **strictement** les contrats externes : payload/réponse `/api/convert`, événements SSE, format `history.json`, nommage `iter_NNN_*.png`, CLI `process.py`.
- Mutualiser une fonction `run_step` entre CLI et serveur pour éviter toute divergence future.
- Réduire de ~33 % le payload de `/api/preview` en passant à un PNG binaire + headers (même pattern que `/api/bgmask`).
- Fournir une entrée `gunicorn` optionnelle sans rendre `gunicorn` obligatoire.

**Non-Goals:**
- Pas de parallélisation des étapes ni des images : le verrou `_active_job` reste en place (un seul job à la fois), le gain visé est sur la latence d'étape, pas sur la concurrence.
- Pas de passage à FastAPI / uvicorn / asyncio : le travail est CPU-bound (NumPy relâche le GIL), un pool de workers gunicorn suffit.
- Pas de cache résultat pour `/api/convert` (contrairement au preview) : les iters doivent **toujours** être recalculés pour obtenir un artefact disque.
- Pas de modification du protocole SSE : les événements `step_start`/`step_done`/`warning`/`done` gardent leur forme exacte.
- Pas de retrait de `process.py` en tant que CLI : `workflow.py` et `batch.py` continuent à s'en servir via `subprocess`.

## Decisions

### D1. Extraire `run_step` dans un module partagé `scripts/apply_step.py`

**Choix :** créer `pixel-lab/scripts/apply_step.py` exposant :
```python
def run_step(src_path: Path, algo: str, method: str,
             params: dict, dst_dir: Path,
             *, name_override: str | None = None) -> tuple[Path, dict]:
    """Charge src_path, applique l'algo, sauve iter_NNN_<algo>_<method>.png
    dans dst_dir, renvoie (chemin_produit, entry_history)."""
```
La fonction encapsule : ouverture, cast de params (`int`/`float`/`bool`), appel à `ALGO_MODULES[algo].METHODS[method](img, **params)`, détermination du prochain `iter_NNN`, sauvegarde PNG, construction de l'entrée d'historique `{algo, method, params, output, timestamp}`.

Consommateurs :
- `scripts/process.py` : imports `run_step`, appelle avec `dst_dir = OUTPUTS_DIR / stem`, met à jour `history.json` lui-même.
- `server/app.py::_run_job` : imports `run_step`, appelle en boucle sur chaque step, met à jour `history.json` de façon groupée.

**Pourquoi :**
- Une seule source de vérité pour le nommage et les casts de params (actuellement dupliqués en partie entre `process.py` et `_apply_step` du serveur).
- Facilite les tests unitaires : `run_step` est pur (pas de dépendance Flask, pas de dépendance CLI).
- Import direct côté serveur = pas de spawn = ordre de grandeur gagné.

**Alternatives considérées :**
- Garder `process.py` comme seule implémentation et continuer à l'appeler en subprocess (statu quo) — rejeté : c'est précisément l'overhead qu'on veut supprimer.
- Exécuter `process.py` via `runpy.run_path` en-process — évite le spawn mais garde la CLI parsing et l'I/O stdout/stderr, coût bureaucratique sans bénéfice vs import direct.

### D2. `_run_job` reste **synchrone et séquentiel**, sans thread worker pool

**Choix :** `_run_job` continue d'itérer `for img in images: for step in pipeline: run_step(...)` dans un unique thread Python (celui que `threading.Thread(target=_run_job, …)` crée déjà aujourd'hui, `app.py:232`). Les événements SSE sont poussés dans la liste `_jobs[job_id]["events"]` au même rythme qu'aujourd'hui.

**Pourquoi :**
- Le verrou `_active_job` impose déjà **un seul job actif à la fois** : paralléliser à l'intérieur d'un job donnerait un gain CPU si les étapes étaient indépendantes, mais **elles ne le sont pas** (chaque étape consomme la sortie de la précédente).
- Paralléliser sur **les images** à l'intérieur d'un même job est possible mais multiplie la complexité (ordre des événements SSE, partage de cache, gestion des erreurs partielles) pour un gain limité en usage mono-utilisateur.
- Le GIL ne bloque pas les opérations NumPy/Pillow lourdes (elles relâchent le GIL en C), donc même à terme, un pool de workers n'est pas strictement nécessaire pour saturer un cœur.

**Alternatives considérées :**
- `concurrent.futures.ProcessPoolExecutor` par image — considéré pour plus tard (`Open Questions`), pas V1.
- `ThreadPoolExecutor` par étape — impossible vu la dépendance séquentielle des steps.

### D3. Format de réponse `/api/preview` : PNG binaire + headers

**Choix :** `/api/preview` renvoie `Content-Type: image/png` avec les métadonnées en headers personnalisés :
- `X-Width: <int>`
- `X-Height: <int>`
- `X-Elapsed-Ms: <int>`
- `X-Cache-Hit-Depth: <int>`

Le corps est le PNG binaire (bytes directs, pas d'encodage intermédiaire).

**Pourquoi :**
- `/api/bgmask` utilise déjà exactement ce pattern (`app.py:611`, headers `X-Cache`, `X-Bgmask-Color`), donc c'est cohérent avec le reste du code.
- Économie de ~33 % de bytes (PNG binaire vs PNG + base64 + JSON wrapping).
- Côté client, `URL.createObjectURL(blob)` est natif, plus rapide qu'un parsing JSON + `data:` URL.
- Les headers custom sont triviaux à lire en JS : `resp.headers.get('X-Elapsed-Ms')`.

**Alternatives considérées :**
- Garder le JSON base64 et ajouter de la compression `Content-Encoding: gzip` — gain marginal (PNG est déjà compressé), complexité supérieure.
- `multipart/mixed` avec PNG + JSON metadata — overkill, pas de support natif dans `fetch`.

### D4. `gunicorn` en dépendance optionnelle, fallback `app.run` conservé

**Choix :** ajouter `gunicorn` dans un extra group de `requirements.txt` (ex. `requirements-prod.txt` ou `[prod]` extra), créer un script `pixel-lab/serve.py` (nom TBD) qui :
1. Essaie d'importer `gunicorn.app.wsgiapp`.
2. Si disponible et variable env `PIXEL_LAB_PROD=1`, lance via `gunicorn -w 2 -b 127.0.0.1:5500 pixel-lab.server.app:app`.
3. Sinon, fallback direct sur `app.run(host="127.0.0.1", port=5500, threaded=True)`.

**Pourquoi :**
- Un seul point d'entrée pour l'utilisateur : le comportement local (pas de gunicorn installé) reste identique à aujourd'hui.
- `gunicorn` apporte : timeouts de worker (évite qu'un job bloqué ne gèle le serveur), recycling (libère la mémoire cache après N requêtes), logs structurés, graceful restart.
- 2 workers suffisent pour usage solo localhost (convert + preview en parallèle via deux workers), sans complexifier le partage d'état (`_active_job`, caches).

**Caveat :** `_active_job` est un global en mémoire process : avec gunicorn multi-workers, ce verrou ne protège plus contre la concurrence inter-workers. Il faut **soit** rester en `-w 1` (un seul worker), **soit** porter le lock vers un mécanisme inter-process (fichier lock, Redis, …) — c'est hors scope V1. **Décision : `-w 1` par défaut** avec un commentaire dans `serve.py`.

**Alternatives considérées :**
- FastAPI + uvicorn — migration plus lourde (décorateurs différents, SSE via `StreamingResponse`, types Pydantic), pas justifiée par le besoin actuel.
- uwsgi — moins répandu que gunicorn dans l'écosystème Flask.

### D5. `process.py` garde sa CLI, mais délègue à `run_step`

**Choix :** `scripts/process.py` reste un script exécutable (`python process.py input.png sharpen method=unsharp_mask …`) consommé par `workflow.py`, `batch.py`, et historiquement par `_run_job`. Son main() parse les arguments positionnels/`key=value` comme aujourd'hui, puis appelle `run_step(...)` de `apply_step.py` au lieu de contenir la logique inline. La mise à jour de `history.json` reste dans `process.py` pour la CLI (pour ne pas faire régresser `workflow.py` qui ne passe pas par le serveur).

**Pourquoi :**
- Zéro rupture pour les consommateurs CLI existants.
- Aucun risque de divergence : le serveur et la CLI appellent la même fonction `run_step`.
- Le test unitaire de la pipeline peut se faire en important `run_step` sans passer par un fork.

**Alternatives considérées :**
- Déprécier `process.py` complètement — rejeté, `workflow.py` et `batch.py` en dépendent.
- Déplacer la mise à jour `history.json` dans `run_step` — rejeté, le serveur veut batcher les updates, la CLI veut updater immédiatement.

### D6. Mise à jour `history.json` côté serveur : append par image, pas par step

**Choix :** `_run_job` accumule les entrées `run_step_entry` en mémoire pendant toute la boucle `for step`, et écrit `history.json` une seule fois par image (après `image_done`) avec un lock léger. Aujourd'hui, `process.py` appelé en subprocess écrit le fichier **à chaque étape** (risque de contention + surcoût disque).

**Pourquoi :**
- Élimine un appel fsync par étape.
- Atomicité : l'historique d'une image est soit complet soit absent, pas de moitié d'itérations bloquée par un crash mid-pipeline (dans ce cas, les iters déjà sur disque restent — c'est acceptable, ils seront re-découvrables ou re-générables).
- Concurrence : un verrou `threading.Lock` protège l'écriture (pas de souci tant qu'on reste en `-w 1` de gunicorn).

**Alternatives considérées :**
- Une écriture à la toute fin du job (après toutes les images) — rejeté, risque de perdre le contexte d'une image si crash au milieu d'une autre.
- Écriture immédiate par step (statu quo comportemental) — coûteux I/O.

### D7. Blob URL côté front + cleanup

**Choix :** `renderPreview` reçoit un `Blob` au lieu d'une `data:` URL :
```js
const blob = await res.blob();
const url = URL.createObjectURL(blob);
if (lastPreviewUrl) URL.revokeObjectURL(lastPreviewUrl);
lastPreviewUrl = url;
previewImg.src = url;
```

Le `URL.revokeObjectURL` du précédent blob est appelé à chaque nouveau preview ET à la désactivation du toggle live (pour libérer la mémoire). Les métadonnées sont lues via `res.headers.get('X-Elapsed-Ms')` etc.

**Pourquoi :**
- Pas de surcoût mémoire tant qu'on révoque les URLs obsolètes.
- Même UX visuelle (l'`<img>` charge l'URL de blob comme une data URL).
- Plus rapide : pas de round-trip JSON parse → atob → data URL.

**Risque :** oubli de révoquer une URL → fuite progressive de mémoire sur les longues sessions. Couvert par `renderPreview` systématiquement + par un revoke au moment du toggle OFF.

## Risks / Trade-offs

- **[Régression fonctionnelle sur `/api/convert`]** → Le changement est invasif : on refait toute la boucle d'orchestration. Mitigation : le test manuel 10.5 du change `add-live-preview` (lancer un batch de 10 images, vérifier `iter_NNN_*.png` + `history.json` identiques à la référence) sera exécuté avant merge. Ajouter un test automatisé (curl + diff) est possible mais hors scope V1.
- **[Divergence de comportement CLI vs serveur après refactor]** → Risque si `process.py` et `_run_job` divergent sur les casts de params ou le nommage. Mitigation : `run_step` est l'unique implémentation, les deux chemins l'appellent avec les mêmes arguments.
- **[Mémoire : le process Flask détient maintenant les images Pillow pendant toute la durée du job]** → Aujourd'hui, chaque subprocess termine et libère sa mémoire au `exit`. En in-process, les références sont libérées au `del` en fin de boucle, mais les pics instantanés sont plus visibles. Mitigation : la boucle utilise des variables locales qui sortent de scope à chaque itération ; GC Python libère en quelques dizaines de ms. Ajouter un `gc.collect()` explicite entre images si nécessaire.
- **[gunicorn multi-worker casserait `_active_job`]** → Documenté D4. On reste `-w 1` par défaut, commentaire clair dans `serve.py`. Si besoin futur de multi-worker, faudra porter le lock.
- **[Front qui continue à s'attendre au JSON base64 pendant la fenêtre de déploiement]** → On met à jour front + back dans la même PR, donc pas de fenêtre. Si besoin de rétrocompatibilité (tests externes, scripts), on peut ajouter `Accept: application/json` mais ça alourdit le code ; décision finale à prendre en revue.
- **[Blob URLs non révoqués → fuite mémoire]** → Mitigation : revoke systématique dans `renderPreview` et dans `setLiveMode(false)`. Doc claire dans le code.

## Migration Plan

Change strictement en-process, pas de migration de données.

1. **Phase 1 — Refactor** : créer `scripts/apply_step.py::run_step`. Faire passer `process.py` par cette fonction tout en gardant son contrat CLI. Vérifier que `workflow.py`/`batch.py` continuent à produire les mêmes `iter_NNN_*.png` en bit-à-bit.
2. **Phase 2 — Intégration serveur** : remplacer la boucle `subprocess.Popen` dans `_run_job` par une boucle `run_step`. Adapter la poussée d'événements SSE (mêmes types, mêmes payloads). Mettre à jour `history.json` par image (cf. D6). Test manuel : batch 10 images × 3 steps, comparer à la référence.
3. **Phase 3 — Format binaire `/api/preview`** : modifier la route pour `Response(png_bytes, mimetype="image/png", headers={...})`. Adapter `firePreview`/`renderPreview` côté front. Vérifier avec `cache_hit_depth > 0` que le cache fonctionne toujours.
4. **Phase 4 — Entrée gunicorn optionnelle** : ajouter `requirements-prod.txt` (ou extra), créer `pixel-lab/serve.py` avec détection + fallback. Documenter le mode prod dans `README.md`. Pas de changement de comportement par défaut (fallback `app.run`).

Rollback : `git revert` du commit suffit. Aucune donnée écrite dans un format nouveau.

Déploiement : outil localhost — l'utilisateur redémarre `python pixel-lab/server/app.py` (ou `python pixel-lab/serve.py` si nouveau script) et la nouvelle version prend effet.

## Open Questions

- **Rétrocompatibilité de `/api/preview`** : faut-il supporter `Accept: application/json` pendant une période pour ne pas casser un éventuel consommateur externe ? Aucun consommateur externe connu aujourd'hui, on peut se permettre un cut clean. À trancher en revue.
- **Test automatisé de non-régression `/api/convert`** : ajouter un test Python (pytest ou unittest) qui compare bit-à-bit les iters produits par l'ancienne et la nouvelle implémentation ? Probablement pas V1 (coût de setup vs bénéfice), mais à envisager si d'autres refactors suivent.
- **Parallélisation future sur les images** : dans quelle mesure `ProcessPoolExecutor` (1 process par image) apporterait-il un gain réel sur un batch de 20–50 images ? À mesurer après V1, coût d'implémentation élevé (ordre SSE, partage `history.json`).
- **Nombre de workers gunicorn** : faut-il proposer `-w 2` par défaut (avec documentation du caveat `_active_job`) ou rester `-w 1` strict ? Prudence → `-w 1` V1.
- **Libération mémoire explicite** : faut-il appeler `gc.collect()` entre images pour éviter les pics mémoire sur batch ? À décider après mesure sur 1024² × 20 images.
