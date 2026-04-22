## Context

Le Pixel Lab est un atelier Python (`pixel-lab/`) qui transforme des sprites pixel-art via 4 familles d'algorithmes (sharpen, scale2x, denoise, pixelsnap). Aujourd'hui, le dashboard `dashboard/index.html` est read-only : il visualise les itérations déjà produites par les CLI `process.py` / `batch.py` / `workflow.py` / `compare_snap.py`. Lancer une nouvelle conversion exige d'ouvrir un terminal et de connaître la syntaxe `algo:method param=value` à la main.

Le projet veut ajouter au dashboard la capacité de déclencher des conversions, avec :
- Multi-sélection des images d'entrée à traiter,
- Choix d'un algo (ou d'un pipeline d'algos chaînés) avec paramètres exposés dans l'UI,
- Suivi de progression en temps réel,
- **Sans** casser les CLI existantes (qui doivent rester exécutables seules).

L'exploration `/opsx:explore` du jour a tranché les choix d'architecture suivants : Flask localhost-only + subprocess vers `process.py` (1 appel par étape) + builder UI à étapes + SSE + presets + `PARAMS` dict co-localisés avec les algorithmes.

## Goals / Non-Goals

**Goals:**
- Permettre de lancer une conversion mono-algo OU pipeline depuis le navigateur.
- Exposer dans l'UI tous les paramètres d'une méthode (radius, percent, block, sigma…) avec leurs bornes et leurs défauts.
- Garantir une séparation stricte back/front : aucun import de code métier dans Flask, aucun import de Flask dans les scripts CLI.
- Préserver à 100 % les usages CLI directs (zéro modification de `process.py`, `workflow.py`, `batch.py`, `compare_snap.py`).
- Mode dégradé : si Flask n'est pas lancé, le dashboard reste utilisable en lecture seule.
- Sécurité minimale : bind 127.0.0.1 + allow-list algos + refus path-traversal + validation params côté serveur.

**Non-Goals:**
- Pas d'authentification / gestion d'utilisateurs (outil personnel localhost).
- Pas de sauvegarde côté serveur des presets utilisateurs (les 3 presets prédéfinis suffisent pour cette V1).
- Pas de gestion de queue persistante / RQ / Celery — un dict `{job_id → state}` en mémoire suffit pour un usage solo localhost.
- Pas de drag-and-drop pour le réordonnancement (boutons `[↑] [↓]` suffisent).
- Pas de refactor des modules `algorithms/*.py` au-delà de l'ajout d'un dict `PARAMS`.
- Pas de remplacement de `serve.py` (continue à servir le dashboard statique en parallèle).

## Decisions

### D1. Flask plutôt que `http.server` stdlib ou FastAPI

**Choix :** Flask (`pip install flask`).

**Pourquoi :**
- `http.server.BaseHTTPRequestHandler` demande beaucoup de boilerplate pour parser le JSON, gérer le routing, et surtout pour streamer du SSE proprement avec threading.
- FastAPI + uvicorn ajoute 2 dépendances et de l'async natif sans bénéfice réel pour un usage solo localhost.
- Flask offre un sweet spot : routing déclaratif, JSON natif, support SSE via `Response(generator(), mimetype='text/event-stream')`, ~150-200 lignes pour tout l'app.

**Alternatives considérées :** `http.server` stdlib (rejeté pour boilerplate SSE), FastAPI + uvicorn (rejeté pour overkill), bottle / falcon (rejeté pour adoption marginale).

### D2. Subprocess vers `process.py` plutôt qu'import direct

**Choix :** `subprocess.Popen(["python", "scripts/process.py", ...])`, 1 appel par étape de pipeline.

**Pourquoi :**
- Réutilise telle quelle toute la logique existante de `process.py` (parsing args, application algo, sauvegarde iter, mise à jour `history.json`).
- Garantit que le chemin "via dashboard" produit exactement les mêmes itérations et entrées d'historique que le chemin "via CLI" — pas de duplication, pas de drift.
- Renforce la séparation back/front par construction : `server/app.py` ne touche pas aux modules `algorithms/`.
- Le coût de spawn (50-100 ms par appel) est négligeable face au temps de traitement réel d'un algo (~100 ms à plusieurs secondes).

**Alternative considérée :** import direct (`from process import apply_algo`) — rejeté car couple le serveur aux modules métier et oblige Flask à reproduire la logique de sauvegarde / d'historique.

### D3. SSE plutôt que WebSocket ou polling

**Choix :** Server-Sent Events (`Content-Type: text/event-stream`).

**Pourquoi :**
- Push unidirectionnel (serveur → client) est exactement ce qu'il faut pour streamer la progression d'un job.
- API navigateur native (`new EventSource(url)`), pas de lib client à inclure.
- HTTP/1.1 standard, traverse n'importe quel proxy / intercepteur.
- Plus simple qu'un WebSocket pour un cas read-only.

**Alternatives considérées :** WebSocket (rejeté pour bidirectionnalité inutile), polling 1s (rejeté pour latence + charge inutile).

### D4. `PARAMS` dict co-localisé plutôt qu'introspection ou JSON externe

**Choix :** Ajouter un attribut `PARAMS` à chaque module `algorithms/*.py`, à côté de `METHODS`.

**Pourquoi :**
- Bornes (`min`, `max`) sémantiques nécessaires côté UI (input HTML5 natif) et côté validation serveur — l'introspection `inspect.signature` ne peut pas les deviner.
- ~12 méthodes au total → maintenance triviale (2-3 lignes par méthode).
- Source unique de vérité co-localisée avec le code qu'elle décrit → impossible de désynchroniser un fichier JSON externe avec le code Python.
- Lue par Flask et sérialisée telle quelle en JSON via `GET /api/algos`. Aucune logique de transformation.

**Alternatives considérées :** introspection (perd les bornes, pas de validation serveur), `algos_meta.json` séparé (désynchronisation garantie).

### D5. Builder à étapes unique plutôt que mode mono-algo + mode pipeline séparés

**Choix :** une seule mécanique d'UI : un builder ordonné où 1 étape équivaut à un mono-algo, N étapes à un pipeline.

**Pourquoi :**
- Une seule UI à coder, à tester, à apprendre.
- Les presets remplissent simplement le builder avec une liste prédéfinie d'étapes.
- L'utilisateur peut toujours ajuster le preset après chargement (pas de "mode" verrouillé).
- Le format du payload `POST /api/convert` est uniforme (`pipeline: [...]`).

**Alternative considérée :** UI à deux modes (radio "Mono / Pipeline") — rejeté pour duplication d'interface et friction de bascule.

### D6. Présets en dur dans le frontend (V1) plutôt que stockage serveur

**Choix :** 3 presets statiques codés dans le JS du dashboard : `Nettoyage GenAI`, `Upscale propre x2`, `Correction JPEG`.

**Pourquoi :**
- Couvre 90 % des cas d'usage réels du lab d'après l'historique.
- Aucun aller-retour serveur, aucune persistance à gérer.
- Si le besoin de presets utilisateurs émerge plus tard, on ajoutera `GET/POST /api/presets` + localStorage côté front sans casser l'existant.

**Alternative considérée :** sauvegarde côté serveur (`pixel-lab/presets.json`) — rejeté pour V1, à reconsidérer si demande utilisateur.

### D7. Mode dégradé sans Flask : `serve.py` reste utilisable

**Choix :** le dashboard détecte l'API hors-ligne en interceptant l'erreur de `GET /api/algos` au chargement, et affiche un message non bloquant. `serve.py` est inchangé et continue à servir le dashboard statique sur 5500.

**Pourquoi :**
- L'utilisateur qui ouvre `serve.py` sans avoir lancé Flask doit comprendre immédiatement pourquoi le panneau "Convertir" est désactivé, sans erreur cryptique.
- Aucune installation forcée de Flask : si l'utilisateur n'en veut pas, le dashboard reste un visualiseur d'itérations comme avant.
- La séparation back/front est ici tangible : retirer le back ne casse pas le front.

### D8. Validation `scale2x` au milieu de pipeline : warning, pas erreur

**Choix :** le serveur logue un warning SSE quand `scale2x` apparaît à une position autre que la dernière, mais continue le pipeline.

**Pourquoi :**
- Confirmé pendant l'exploration : permissif par défaut, l'utilisateur reste libre.
- Un upscale en milieu de chaîne est rare mais pas absurde (ex. débruiter une image upscalée).
- Une erreur 400 stricte serait paternaliste pour un outil personnel.

## Risks / Trade-offs

- **[Exécution de scripts via HTTP]** → Mitigations multiples : bind strict 127.0.0.1, allow-list algos, validation basename uniquement, validation params contre `PARAMS`. Impossible d'exécuter du code arbitraire via cet endpoint.
- **[Conflits sur `iter_NNN` si jobs concurrents touchent la même image]** → V1 : exécution séquentielle d'un seul job à la fois (lock global en mémoire). Si l'utilisateur lance un nouveau job pendant qu'un précédent tourne, le serveur renvoie `409 Conflict`. Suffisant pour un outil solo localhost.
- **[Coût de spawn × N étapes × M images]** → ~100 ms × N × M, négligeable devant le temps réel de traitement (typiquement secondes à minutes pour les algos lourds).
- **[Perte de progression si le client SSE se déconnecte]** → Le job continue côté serveur. Le client peut se reconnecter avec le même `job_id` et recevra à nouveau les événements à partir de l'état courant (rediffusion de l'état + futurs events).
- **[`PARAMS` désynchronisé avec la signature Python]** → Test unitaire simple (boucle sur `inspect.signature(fn)` et compare avec `PARAMS[<name>]`). À ajouter dans les tasks.
- **[Mode dégradé silencieux]** → L'avertissement "API hors-ligne" doit être visible et expliquer comment démarrer Flask, sinon l'utilisateur ne comprend pas pourquoi rien ne se passe.

## Migration Plan

Aucune migration de données. La V1 est strictement additive :
1. Ajout de `pixel-lab/server/app.py`, `pixel-lab/requirements.txt`, et du panneau dans `dashboard/index.html`.
2. Extension de `algorithms/*.py` avec un `PARAMS` dict (additif, ne casse aucune signature).
3. Aucun script CLI existant n'est modifié.
4. Lancement : `pip install -r pixel-lab/requirements.txt` puis `python pixel-lab/server/app.py` (et `python pixel-lab/serve.py` pour le statique, comme avant).

Rollback : supprimer `pixel-lab/server/`, retirer le panneau du `dashboard/index.html`, retirer les `PARAMS` dicts. Aucune dépendance externe (autre que Flask) n'est introduite ailleurs.

## Open Questions

- **Configuration de port** : faut-il rendre le port Flask configurable via env var `PIXEL_LAB_PORT` ou via argument CLI `--port` ? Défaut 5500 conflicte avec `serve.py` — on choisit 5501 pour Flask, mais à confirmer avant codage.
- **Concurrence multi-jobs** : V1 verrouille à 1 job actif. Si l'utilisateur veut paralléliser images dans un même job, c'est OK ; si l'utilisateur veut soumettre 2 jobs distincts en parallèle, on rejette en 409. À reconsidérer si l'usage réel demande mieux.
