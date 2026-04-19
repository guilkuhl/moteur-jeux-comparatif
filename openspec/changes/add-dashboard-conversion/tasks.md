## 1. Métadonnée des paramètres dans les modules algorithms

- [ ] 1.1 Ajouter le dict `PARAMS` dans `pixel-lab/scripts/algorithms/sharpen.py` pour `unsharp_mask`, `laplacian`, `kernel` (champs `name`, `type`, `default`, `min`, `max`)
- [ ] 1.2 Ajouter le dict `PARAMS` dans `pixel-lab/scripts/algorithms/scale2x.py` pour `nearest`, `scale2x`, `eagle2x` (entrées vides si pas de param exposé)
- [ ] 1.3 Ajouter le dict `PARAMS` dans `pixel-lab/scripts/algorithms/denoise.py` pour `median`, `bilateral`, `nlm`
- [ ] 1.4 Ajouter le dict `PARAMS` dans `pixel-lab/scripts/algorithms/pixelsnap.py` pour `median`, `mode`, `mean`
- [ ] 1.5 Vérifier manuellement la cohérence default Python ↔ default `PARAMS` pour les 12 méthodes
- [ ] 1.6 Ajouter un test unitaire `pixel-lab/scripts/algorithms/test_params.py` qui boucle sur `inspect.signature(fn)` et compare aux defaults `PARAMS[name]`

## 2. Backend Flask

- [ ] 2.1 Créer `pixel-lab/requirements.txt` déclarant `Flask>=3.0`
- [ ] 2.2 Créer `pixel-lab/server/__init__.py` vide
- [ ] 2.3 Créer `pixel-lab/server/app.py` avec un Flask minimal liant `127.0.0.1:5501`
- [ ] 2.4 Implémenter `GET /api/inputs` : list `pixel-lab/inputs/*.{png,jpg,jpeg,bmp,webp,tga}`, retour JSON avec flag `processed` lu depuis `history.json`
- [ ] 2.5 Implémenter `GET /api/algos` : importer dynamiquement les 4 modules et sérialiser `{algo: {methods: {method: {params: PARAMS[method]}}}}`
- [ ] 2.6 Implémenter la validation centrale (allow-list algos, basename images, types/bornes params contre `PARAMS`) — fonction `validate_payload(payload) -> (ok, errors)`
- [ ] 2.7 Implémenter `POST /api/convert` : valide, génère `job_id` UUID, démarre un thread d'orchestration en arrière-plan, retourne `202 {job_id}`
- [ ] 2.8 Implémenter le store de jobs en mémoire `{job_id → {state, queue, events}}` avec lock pour rejet `409 Conflict` si un job est déjà actif
- [ ] 2.9 Implémenter l'orchestrateur thread : pour chaque image × étape, spawn `python scripts/process.py <input> <algo> method=<m> [k=v...]`, capture stdout/stderr, push événement dans la queue
- [ ] 2.10 Implémenter le chaînage : pour les étapes 2..N, lire le dernier `iter_NNN_*.png` produit par l'étape précédente comme `<input>`
- [ ] 2.11 Implémenter le warning `scale2x` au milieu de pipeline : push événement SSE `{type:"warning", message:"..."}` avant le step concerné
- [ ] 2.12 Implémenter `GET /api/jobs/<id>/stream` : flux SSE qui consomme la queue du job et émet `step_start`, `step_done`, `step_error`, `image_done`, `warning`, `done`
- [ ] 2.13 Gérer la rediffusion d'état pour un client qui se reconnecte au stream après une déconnexion (re-émission de l'historique d'événements puis poursuite)

## 3. Frontend dashboard

- [ ] 3.1 Ajouter dans `dashboard/index.html` une checkbox `<input type="checkbox" class="img-select">` dans chaque `.img-item` de la sidebar, avec compteur "N sélectionnée(s)" en footer de sidebar
- [ ] 3.2 Ajouter une région `.convert-panel` dans le main-layout avec en-tête "Convertir", liste d'étapes vide à 1 entrée par défaut, bouton `+ Ajouter une étape`, dropdown `Charger un preset`, bouton `[▶ Lancer]`
- [ ] 3.3 Au chargement, fetch `GET /api/algos` et stocker le catalogue en JS ; en cas d'erreur réseau, basculer en mode dégradé (panneau désactivé + message)
- [ ] 3.4 Implémenter le composant "étape" : sélecteur `<select algo>`, sélecteur `<select method>` filtré, contrôles `[×] [↑] [↓]`, zone d'inputs paramètres réactive
- [ ] 3.5 Implémenter la génération des inputs paramètres à partir de `PARAMS[<method>]` : `<input type="number" min max step value=<default>>` avec label
- [ ] 3.6 Implémenter le reset des inputs au changement de méthode (les anciens disparaissent, les nouveaux apparaissent avec defaults)
- [ ] 3.7 Coder en dur les 3 presets en JS : `Nettoyage GenAI`, `Upscale propre x2`, `Correction JPEG` ; sélection remplit le builder en remplaçant son contenu
- [ ] 3.8 Implémenter le clic `[▶ Lancer]` : assemble le payload `{images, pipeline}`, POST `/api/convert`, récupère `job_id`, ouvre `EventSource('/api/jobs/<id>/stream')`
- [ ] 3.9 Implémenter le rendu live des événements SSE : barre de progression `N/M`, ligne par image avec icône (en cours / OK / erreur), bloc d'erreur `stderr` tronqué pour les `step_error`
- [ ] 3.10 À la réception de l'événement `done`, refetch `GET /api/inputs` + recharger les iterations de l'image active dans la zone de comparaison (sans reload page)
- [ ] 3.11 Mode dégradé : si `GET /api/algos` échoue, afficher message "API hors-ligne — démarre `python pixel-lab/server/app.py`" dans le panneau, désactiver visuellement (greyed out) le bouton `[▶ Lancer]` et les sélecteurs

## 4. Sécurité et robustesse

- [ ] 4.1 Vérifier que `app.run(host="127.0.0.1", port=5501)` est utilisé partout (jamais `0.0.0.0`)
- [ ] 4.2 Tester manuellement le refus path-traversal : `POST /api/convert` avec `images:["../../../etc/passwd"]` doit renvoyer 400
- [ ] 4.3 Tester manuellement le refus algo hors allow-list : `POST` avec `algo:"rm -rf /"` doit renvoyer 400
- [ ] 4.4 Tester manuellement le refus param hors bornes : `POST` avec `params:{block:99999}` doit renvoyer 400 mentionnant le param fautif
- [ ] 4.5 Tester le rejet `409 Conflict` quand un job est déjà actif

## 5. Documentation et lancement

- [ ] 5.1 Ajouter dans `pixel-lab/README.md` (créer si absent) une section "Dashboard interactif" : installer Flask, lancer `serve.py` + `server/app.py`, ouvrir le navigateur
- [ ] 5.2 Mentionner les ports utilisés (5500 pour `serve.py` statique, 5501 pour Flask API) et comment les changer
- [ ] 5.3 Documenter le mode dégradé (dashboard utilisable sans Flask en lecture seule)

## 6. Validation OpenSpec

- [ ] 6.1 Lancer `openspec validate --change add-dashboard-conversion --strict` et corriger les éventuelles erreurs
- [ ] 6.2 Lancer `openspec validate --specs --strict` après archive pour vérifier la cohérence des specs principales mises à jour
- [ ] 6.3 Lancer `openspec status --change add-dashboard-conversion` et confirmer `isComplete: true` une fois toutes les tasks cochées

## 7. Test end-to-end manuel

- [ ] 7.1 Lancer `pip install -r pixel-lab/requirements.txt`
- [ ] 7.2 Démarrer `python pixel-lab/server/app.py` puis `python pixel-lab/serve.py`
- [ ] 7.3 Ouvrir `http://localhost:5500/dashboard/index.html`, cocher 1 image, sélectionner mono-algo `pixelsnap/median block=4`, cliquer Lancer, vérifier qu'une nouvelle iter apparaît dans la sidebar et la zone de comparaison
- [ ] 7.4 Charger le preset `Nettoyage GenAI`, cocher 2 images, lancer, vérifier la progression SSE et l'apparition de 6 nouvelles iters (2 images × 3 étapes)
- [ ] 7.5 Arrêter Flask et recharger le dashboard, vérifier que le mode dégradé s'affiche correctement (lecture seule fonctionne, panneau Convert désactivé avec message)
- [ ] 7.6 Vérifier que les CLI restent fonctionnelles : `python scripts/process.py inputs/test_blurry.png pixelsnap method=median` doit produire une iter standalone sans serveur
