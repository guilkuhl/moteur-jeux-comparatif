## Why

Aujourd'hui, lancer une conversion sur les images de `pixel-lab/inputs/` exige d'ouvrir un terminal et de taper la commande `process.py`/`workflow.py`/`batch.py` à la main, sans visibilité sur les algorithmes disponibles ni leurs paramètres. Le dashboard est read-only : il sert à comparer les résultats déjà produits, jamais à en produire. Cette friction casse la boucle de feedback rapide qui fait l'intérêt d'un lab interactif, surtout quand le bon traitement est un pipeline multi-étapes.

L'objectif est d'ouvrir le déclenchement des conversions depuis le navigateur — sélection visuelle des images d'entrée, choix d'un algorithme ou d'un pipeline d'algorithmes avec paramètres exposés dans l'IHM, suivi en temps réel — sans casser les usages CLI directs ni mélanger logique back et front.

## What Changes

- **NEW** Backend HTTP Flask (`pixel-lab/server/app.py`) qui expose `/api/inputs`, `/api/algos`, `/api/convert` (POST) et `/api/jobs/<id>/stream` (SSE). Bind strict `127.0.0.1`.
- **NEW** Panneau "Convertir" dans le dashboard avec :
  - Multi-sélection des images d'entrée (cases à cocher dans la sidebar existante).
  - Builder à étapes : 1 étape = mono-algo, N étapes = pipeline. Réordonnable, supprimable, avec presets prédéfinis (Nettoyage GenAI, Upscale propre x2, Correction JPEG).
  - Champs de paramètres dynamiques par méthode (radius, percent, block, sigma_color, …) avec types et bornes natives HTML5.
  - Suivi de progression en temps réel via SSE, auto-refresh de la sidebar et de la zone de comparaison après chaque job.
- **NEW** Métadonnée `PARAMS` ajoutée dans chaque module `pixel-lab/scripts/algorithms/*.py` pour décrire les paramètres exposables (nom, type, défaut, min, max). Source unique de vérité, lue par Flask et sérialisée en JSON.
- **NEW** Mode dégradé : `serve.py` continue à servir le dashboard en lecture seule si Flask n'est pas lancé, les boutons "Lancer" sont désactivés avec un avertissement clair.
- **MODIFIED** Le dashboard `dashboard/index.html` n'est plus purement read-only : il appelle l'API quand elle est disponible, sans rien casser à l'affichage existant.
- **PAS DE BREAKING CHANGE** : `process.py`, `batch.py`, `workflow.py`, `compare_snap.py` restent inchangés et exécutables directement en CLI.

## Capabilities

### New Capabilities
- `pixel-art-conversion-api` : Backend HTTP local (Flask) qui expose le catalogue des algorithmes/paramètres et orchestre l'exécution des conversions par sous-processus, avec streaming SSE de la progression et validation stricte (allow-list algos, refus de path-traversal sur les noms d'images).

### Modified Capabilities
- `pixel-art-algorithms` : Ajout d'une métadonnée `PARAMS` dans chaque module pour décrire les paramètres exposables au format `[{name, type, default, min, max}, ...]`. Source unique pour la génération du formulaire frontend et la validation backend.
- `pixel-art-dashboard` : Le dashboard cesse d'être uniquement read-only. Il intègre un panneau "Convertir" avec multi-sélection d'images, builder de pipeline à étapes, champs de paramètres dynamiques, presets, et consommation du flux SSE de progression. Mode dégradé documenté quand Flask n'est pas lancé.

## Impact

- **Code touché**
  - `pixel-lab/server/app.py` (nouveau, ~150-200 lignes Flask)
  - `pixel-lab/scripts/algorithms/sharpen.py`, `scale2x.py`, `denoise.py`, `pixelsnap.py` (ajout `PARAMS` dict)
  - `pixel-lab/dashboard/index.html` (ajout panneau Convertir + JS d'orchestration)
  - `pixel-lab/requirements.txt` (nouveau, déclare `Flask`)
- **APIs nouvelles** : 4 routes HTTP localhost-only (`GET /api/inputs`, `GET /api/algos`, `POST /api/convert`, `GET /api/jobs/<id>/stream`).
- **Dépendances** : ajout de Flask comme seule nouvelle dépendance Python. Pas d'impact sur les CLI (Flask n'est pas importé par `scripts/*.py`).
- **Sécurité** : exécution de scripts via HTTP — mitigation par bind strict `127.0.0.1`, allow-list des algos, validation des noms d'images (basename uniquement, refus de `..` et `/`), validation des params contre `PARAMS` côté serveur.
- **Pas de migration de données** : `history.json` et `outputs/` continuent d'être utilisés tels quels.
- **Compatibilité descendante** : tous les usages CLI existants restent fonctionnels sans modification.
