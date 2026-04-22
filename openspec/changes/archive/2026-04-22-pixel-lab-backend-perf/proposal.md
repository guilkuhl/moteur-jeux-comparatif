## Why

Le backend `pixel-lab/server/app.py` a trois surcoûts de performance connus, diagnostiqués pendant la revue de la communication back/front :

1. **Subprocess par étape de pipeline dans `_run_job`** (`app.py:287`). Chaque étape d'un pipeline `/api/convert` relance un interpréteur Python complet (`sys.executable scripts/process.py …`) qui ré-importe Pillow et NumPy à froid. Coût mesuré empiriquement : **~100–300 ms de démarrage + réimport par étape**, appliqué à chaque image × chaque étape. Sur un pipeline typique `[pixelsnap, denoise, sharpen]` lancé sur 10 images, c'est 30 forks → 3–9 s de pur overhead de spawn avant toute ligne de calcul utile. La preview (`/api/preview`) a déjà démontré qu'un appel in-process via `_apply_step` (`app.py:454`) donne le même résultat à coût de spawn nul.
2. **Transport base64 sur `/api/preview`** (`app.py:467`). Le PNG est encodé en base64 puis sérialisé dans un JSON, ce qui ajoute **~33 % de bytes** et un cycle encode/décode inutile côté client. La route `/api/bgmask` (`app.py:579`) renvoie déjà un PNG binaire direct avec métadonnées en headers — le même pattern s'applique naturellement au preview.
3. **Serveur Flask de développement** (`app.run(..., debug=False, threaded=True)`, `app.py:1464`). Mono-process, pas de supervision, pas de reload propre, et `_active_job` sérialise déjà les jobs — donc un passage à un serveur WSGI de production (gunicorn) améliorerait la robustesse (timeouts, crash recovery, logs) sans changer la logique.

Priorité : le point (1) est le gain dominant (facteurs 2–10× sur un batch multi-images / multi-étapes). Les points (2) et (3) sont des améliorations marginales mais peu coûteuses à livrer ensemble.

## What Changes

- **MODIFIED** `pixel-lab/server/app.py` : remplacer la boucle `subprocess.Popen(process.py, …)` dans `_run_job` par un appel direct à une nouvelle fonction `_run_step_inprocess(img_path, algo, method, params, out_path) → Path` qui :
  - charge l'image via `Image.open`,
  - applique le step via `_apply_step` (déjà existant, factorisé par le preview),
  - sauvegarde sous `outputs/<stem>/iter_NNN_<algo>_<method>.png` (même nommage qu'aujourd'hui),
  - met à jour `history.json` (via une fonction `_append_history_entry` extraite des responsabilités actuelles de `process.py`).
- **MODIFIED** `pixel-lab/scripts/process.py` : inchangé en surface (reste utilisable en CLI et par `workflow.py`/`batch.py`), mais la logique d'application d'un step et de nommage de l'iter est **extraite dans un module partagé** `pixel-lab/scripts/apply_step.py` (ou intégrée dans `algorithms/__init__.py`) consommé à la fois par `process.py` et `server/app.py`. Aucun changement de contrat CLI.
- **MODIFIED** `/api/preview` : réponse passée de `{png_base64, width, height, elapsed_ms, cache_hit_depth}` à un PNG binaire (`Content-Type: image/png`) avec métadonnées en headers (`X-Width`, `X-Height`, `X-Elapsed-Ms`, `X-Cache-Hit-Depth`). Le front remplace le décodage base64 par un `URL.createObjectURL(blob)`.
- **MODIFIED** `pixel-lab/dashboard/index.html` : adapter `firePreview`/`renderPreview` (lignes 2005–2045) pour consommer le blob PNG au lieu du JSON base64. Libération du blob URL au remplacement (éviter les fuites mémoire).
- **NEW** Intégration d'un serveur WSGI de production : ajout d'une entrée de lancement `python -m pixel-lab.server.wsgi` ou d'un script `serve.py` qui route vers `gunicorn` si disponible, sinon fallback sur `app.run` (comportement actuel). Ajout de `gunicorn` dans `pixel-lab/requirements.txt` en dépendance optionnelle (extra).
- **PAS DE BREAKING CHANGE sur les contrats API** : payload `/api/convert` inchangé, flux SSE `/api/jobs/<id>/stream` inchangé (mêmes événements `step_start`/`step_done`/`step_error`/`done`/`warning`), format `history.json` inchangé, nommage `iter_NNN_*.png` inchangé. Le seul changement observable côté front est le format de réponse de `/api/preview`.
- **COMPATIBILITÉ DESCENDANTE côté front** : pendant la fenêtre de déploiement, `/api/preview` pourra accepter un header `Accept: application/json` et renvoyer l'ancien format base64 si nécessaire — à évaluer en revue (cf. Open Questions du design).

## Capabilities

### New Capabilities
_Aucune nouvelle capability._

### Modified Capabilities
- `pixel-art-conversion-api` : suppression de l'exécution par subprocess dans l'orchestrateur `/api/convert`, passage à un calcul in-process mutualisé avec `/api/preview` ; changement du format de réponse de `/api/preview` (JSON base64 → PNG binaire + headers).

## Impact

- **Code touché**
  - `pixel-lab/server/app.py` : réécriture de `_run_job` et `_run_step_inprocess` (~80 lignes), modification de `/api/preview` pour renvoyer un blob (~15 lignes).
  - `pixel-lab/scripts/process.py` : refactor pour extraire la logique partagée (~30 lignes déplacées).
  - Nouveau fichier `pixel-lab/scripts/apply_step.py` (ou équivalent) : ~60 lignes.
  - `pixel-lab/dashboard/index.html` : adaptation de `firePreview`/`renderPreview` et cleanup du blob URL (~20 lignes).
  - `pixel-lab/requirements.txt` : ajout optionnel de `gunicorn`.
- **APIs modifiées** : 1 route (`POST /api/preview`, changement de format de réponse). Les autres routes sont inchangées.
- **Dépendances** : `gunicorn` ajouté en optionnel (le fallback `app.run` reste fonctionnel sans).
- **Sécurité** : surface inchangée côté inputs ; la suppression des subprocess **réduit** la surface (plus de passage de paramètres par ligne de commande, donc plus de risque d'injection shell même si la construction actuelle est déjà safe).
- **Performance** : gain attendu de 2–10× sur les jobs `/api/convert` multi-étapes, selon le nombre d'étapes. Gain de ~33 % sur le transport `/api/preview` en bytes, et économie d'un cycle base64 décode côté client (marginal sur petites previews, sensible en full-res). Passage à gunicorn : gain de robustesse (timeouts, worker recycling), pas de gain de latence en usage mono-utilisateur.
- **Migration de données** : aucune. Format `history.json`, nommage `iter_NNN_*.png`, structure `outputs/` strictement inchangés.
- **Compatibilité descendante** : le front est mis à jour dans le même change. Les autres consommateurs éventuels de `/api/preview` (aucun connu aujourd'hui) devront passer sur le format binaire.
- **Rollback** : simple `git revert` ; le refactor in-process n'ajoute pas de migration irréversible.
