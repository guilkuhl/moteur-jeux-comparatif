## 1. Extraction de `run_step` dans un module partagé

- [ ] 1.1 Créer `pixel-lab/scripts/apply_step.py` avec la signature `run_step(src_path, algo, method, params, dst_dir, *, name_override=None) → (Path, dict)` — charge l'image, cast les params, appelle `ALGO_MODULES[algo].METHODS[method]`, sauvegarde `iter_NNN_<algo>_<method>.png` dans `dst_dir`, renvoie `(chemin, entry_history)`
- [ ] 1.2 Déplacer la logique de détection du prochain `iter_NNN` (actuellement dans `process.py`) dans `apply_step.py::_next_iter_index(dst_dir)`
- [ ] 1.3 Déplacer la logique de cast de params int/float/bool (actuellement dans `_apply_step` de `app.py:454` et dupliquée partiellement dans `process.py`) dans `apply_step.py::_cast_params`
- [ ] 1.4 Vérifier en test manuel que `run_step` importée depuis un REPL produit exactement le même octet-à-octet PNG qu'un appel `python scripts/process.py input.png sharpen method=unsharp_mask radius=1.2 percent=200` (diff binaire `cmp`)

## 2. Mettre à jour `process.py` pour consommer `run_step`

- [ ] 2.1 Modifier `scripts/process.py::main()` pour parser ses args comme aujourd'hui, puis appeler `apply_step.run_step(...)` au lieu d'inliner la logique
- [ ] 2.2 Conserver la mise à jour de `history.json` dans `process.py` (comportement CLI inchangé — `workflow.py`/`batch.py` s'y attendent)
- [ ] 2.3 Lancer `workflow.py` et `batch.py` sur un input de référence, vérifier via `git diff` ou `cmp` que les `iter_NNN_*.png` produits sont bit-à-bit identiques à la version avant refactor
- [ ] 2.4 Vérifier que `history.json` après un run CLI est strictement identique (ordre des clés, timestamps mis à part) à la référence

## 3. Remplacer `subprocess` par `run_step` dans `_run_job`

- [ ] 3.1 Importer `run_step` dans `server/app.py` (import unique en tête de fichier, à côté des imports `algorithms`)
- [ ] 3.2 Réécrire la boucle `for step_idx, step in enumerate(pipeline)` dans `_run_job` (`app.py:253-315`) pour :
  - supprimer le bloc `subprocess.Popen(...)` + `proc.communicate()`,
  - appeler `run_step(Path(last_input), algo, method, params, OUTPUTS_DIR / img_stem, name_override=img_stem if step_idx > 0 else None)`,
  - gérer les exceptions : `try/except Exception as e` → pousser un événement `step_error` avec `str(e)` tronqué à 500 chars (même forme que `stderr[:500]` actuel),
  - mettre à jour `last_input` avec le chemin retourné (remplace `_find_latest_iter`),
  - pousser l'événement `step_done` avec `output: produced_path.name`
- [ ] 3.3 Accumuler les `entry_history` retournés par `run_step` dans une liste par image, et écrire `history.json` une seule fois à la fin de chaque image (après l'événement `image_done`), sous un `threading.Lock` léger
- [ ] 3.4 Supprimer la fonction `_find_latest_iter` si elle n'est plus utilisée ailleurs (grep préalable)
- [ ] 3.5 Test manuel : lancer un `/api/convert` avec `images=["sprite.png"]` et `pipeline=[{pixelsnap}, {denoise}, {sharpen}]`, vérifier :
  - les 3 `iter_NNN_*.png` sont produits avec la même convention de nommage qu'avant,
  - `history.json` contient 3 runs dans l'ordre (comme avant),
  - les événements SSE `step_start`/`step_done` arrivent dans l'ordre attendu,
  - `elapsed` total est ≤ 50 % du temps avant refactor (gain spawn Python)
- [ ] 3.6 Test manuel de robustesse : lancer `/api/convert` avec un param invalide pour déclencher une erreur en milieu de pipeline, vérifier qu'un `step_error` est bien émis et que le pipeline continue sur les étapes suivantes (comportement actuel)

## 4. Changer le format de réponse de `/api/preview` en PNG binaire

- [ ] 4.1 Dans `app.py::api_preview()` (ligne ~502), remplacer le `jsonify({"png_base64": …})` final par `Response(png_bytes, mimetype="image/png", headers={...})` où `png_bytes` est obtenu via `buf = io.BytesIO(); current.save(buf, format="PNG"); buf.getvalue()`
- [ ] 4.2 Ajouter les headers `X-Width`, `X-Height`, `X-Elapsed-Ms`, `X-Cache-Hit-Depth` avec les valeurs actuellement renvoyées dans le JSON
- [ ] 4.3 Supprimer la fonction `_encode_png_base64` si elle n'est plus utilisée ailleurs (grep préalable)
- [ ] 4.4 Vérifier avec `curl -v` que la réponse a bien `Content-Type: image/png`, que les headers custom sont présents, et que le corps est un PNG valide (`file -` sur la sortie)

## 5. Adapter le front à la nouvelle réponse `/api/preview`

- [ ] 5.1 Dans `dashboard/index.html` (autour de la ligne 2005), modifier la gestion de la réponse : `if (!res.ok) { const data = await res.json(); … }` (l'erreur reste JSON) `else { const blob = await res.blob(); renderPreview(blob, res.headers, srcName, pipeline); }`
- [ ] 5.2 Dans `renderPreview`, créer `const url = URL.createObjectURL(blob);`, libérer la précédente URL via `URL.revokeObjectURL(lastPreviewUrl)` si définie, stocker `lastPreviewUrl = url`, mettre `previewImg.src = url`
- [ ] 5.3 Remplacer les lectures de `data.width`, `data.height`, `data.elapsed_ms`, `data.cache_hit_depth` par `headers.get('X-Width')`, etc. — attention au cast en int (`parseInt(…)`)
- [ ] 5.4 Dans `setLiveMode(false)` (désactivation du toggle live), révoquer `lastPreviewUrl` et remettre `lastPreviewUrl = null` pour libérer la mémoire
- [ ] 5.5 Test manuel : toggler live sur 10 images successivement, ouvrir DevTools → Memory, vérifier qu'aucun blob URL ne reste dans `performance.memory` après toggle OFF

## 6. Entrée serveur gunicorn optionnelle

- [ ] 6.1 Créer `pixel-lab/requirements-prod.txt` contenant `gunicorn>=21` (ou ajouter un extra dans `requirements.txt` si le format le permet)
- [ ] 6.2 Créer `pixel-lab/serve.py` qui :
  - lit `os.environ.get("PIXEL_LAB_PROD", "0")`,
  - si `=="1"`, importe et lance gunicorn en `sys.argv = ["gunicorn", "-w", "1", "-b", "127.0.0.1:5500", "server.app:app"]` puis `gunicorn.app.wsgiapp.run()`,
  - sinon, importe `server.app` et appelle `app.run(host="127.0.0.1", port=5500, threaded=True)`
- [ ] 6.3 Ajouter un commentaire explicite dans `serve.py` : « `_active_job` est un global mémoire, ne pas passer à `-w > 1` sans porter le lock »
- [ ] 6.4 Mettre à jour `pixel-lab/README.md` avec : `PIXEL_LAB_PROD=1 python serve.py` pour le mode prod, `python serve.py` (ou `python server/app.py`) pour le mode dev
- [ ] 6.5 Test manuel : `pip install -r requirements-prod.txt && PIXEL_LAB_PROD=1 python pixel-lab/serve.py`, vérifier que gunicorn démarre, que `/api/inputs` répond, et qu'un `/api/convert` complet s'exécute normalement

## 7. Validation globale

- [ ] 7.1 Lancer un batch de 10 images × 3 étapes via le dashboard et mesurer le temps total ; comparer à la mesure de référence avant refactor ; consigner le ratio dans une note interne
- [ ] 7.2 Vérifier qu'aucun fichier n'a été modifié en dehors des scopes attendus : `git status` doit ne montrer que `pixel-lab/server/app.py`, `pixel-lab/scripts/process.py`, `pixel-lab/scripts/apply_step.py`, `pixel-lab/dashboard/index.html`, `pixel-lab/serve.py`, `pixel-lab/requirements*.txt`, `pixel-lab/README.md`, et les fichiers openspec de ce change
- [ ] 7.3 Relire les spec deltas (`specs/pixel-art-conversion-api/spec.md`) et vérifier que tous les scénarios sont couverts par les tâches 3, 4, 5
- [ ] 7.4 Rédiger un court paragraphe dans le commit de merge résumant : (a) gain de temps mesuré, (b) changement de format `/api/preview`, (c) absence de régression sur `/api/convert`
