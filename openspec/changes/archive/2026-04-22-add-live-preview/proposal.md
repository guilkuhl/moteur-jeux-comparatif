## Why

Aujourd'hui, affiner les paramètres d'un pipeline dans le panneau "Convertir" exige de cliquer sur "▶ Lancer" à chaque essai : chaque tweak de `radius`, `percent`, `sigma_color` produit un `iter_NNN_*.png` persisté dans `outputs/` et une entrée dans `history.json`. La boucle de feedback est lente (subprocess + écriture disque + SSE) et pollue l'historique avec des dizaines d'itérations intermédiaires qui n'ont de valeur qu'au moment du tuning. Le `git status` actuel montre déjà 22 itérations supprimées à la main, symptôme d'un outil qui mélange "exploration" et "résultat à garder".

L'objectif est d'ouvrir un **mode live preview** : on construit un pipeline comme aujourd'hui, on bascule en mode live, on tweake les paramètres avec sliders/champs, et on voit le rendu final se mettre à jour en ~200-500 ms sans produire aucun fichier. Quand le réglage est bon, on clique sur "▶ Lancer" existant qui produit l'iter officiel — inchangé.

## What Changes

- **NEW** Endpoint backend `POST /api/preview` dans `pixel-lab/server/app.py`. Payload `{image, pipeline, downscale}`. Réponse = PNG base64 + méta (temps de calcul, dimensions). **Import direct** des modules `algorithms/*.py` (zéro subprocess, zéro écriture disque, zéro update de `history.json`).
- **NEW** Cache serveur des étapes bakées. Clé = hash(image source, préfixe de pipeline). Quand l'utilisateur tweake la dernière étape d'un pipeline à N étapes, seule cette dernière étape est recalculée ; les préfixes figés sont lus depuis le cache.
- **NEW** Notion d'**image active** dans la sidebar du dashboard, distincte de la multi-sélection pour Convert. La miniature cliquée devient l'image de tuning, avec indicateur visuel. La multi-sélection (checkbox) reste pour le batch officiel.
- **NEW** Toggle "Live preview" dans le panneau Convertir. Quand activé :
  - Chaque `onInput`/`onChange` sur les champs de paramètres déclenche un `fetch /api/preview` debouncé à 200 ms.
  - `AbortController` côté client annule les requêtes en vol dès qu'une nouvelle part.
  - Un indicateur d'état non bloquant (dot gris → jaune "calcul" → vert "prêt") remplace tout spinner plein écran.
  - Le PNG renvoyé s'affiche dans la zone de comparaison principale, à côté de l'image source.
- **NEW** Downscale par défaut à 256 px (longueur max) côté serveur pour accélérer le preview. Toggle "Taille réelle" dans l'UI pour forcer plein résolution quand l'utilisateur veut vérifier un algo taille-dépendant (`scale2x`, `pixelsnap/block`).
- **MODIFIED** Le panneau Convertir conserve son bouton "▶ Lancer" inchangé : il continue à produire `iter_NNN_*.png` + maj `history.json` via subprocess `process.py` (décision D2 préservée, source de vérité officielle).
- **PAS DE BREAKING CHANGE** : `process.py`, `batch.py`, `workflow.py`, `compare_snap.py`, `serve.py`, endpoint `/api/convert` et dashboard read-only restent strictement inchangés. Le mode live est strictement additif et désactivable.

## Capabilities

### New Capabilities
_Aucune nouvelle capability : tout le change est un delta sur les capabilities existantes._

### Modified Capabilities
- `pixel-art-conversion-api` : ajout de l'endpoint `POST /api/preview` (import direct des algos, réponse PNG base64 volatile sans persistance) et d'un cache serveur des préfixes de pipeline. L'endpoint `/api/convert` existant reste strictement inchangé.
- `pixel-art-dashboard` : ajout d'un toggle "Live preview" dans le panneau Convertir, introduction de la notion d'**image active** (miniature cliquée, distincte de la multi-sélection par checkbox), debounce 200 ms + `AbortController` sur les inputs de paramètres, indicateur d'état non bloquant, zone d'affichage du preview, toggle "Taille réelle" pour désactiver le downscale.

## Impact

- **Code touché**
  - `pixel-lab/server/app.py` : nouvelle route `/api/preview`, nouveau cache en mémoire (~80-120 lignes).
  - `pixel-lab/dashboard/index.html` : toggle live, logique debounce + abort, état "image active", zone d'affichage preview, toggle taille réelle (~150-200 lignes JS + CSS).
  - `pixel-lab/scripts/algorithms/*.py` : **aucune modification** (les modules sont importés tels quels).
- **APIs nouvelles** : 1 route HTTP localhost-only (`POST /api/preview`).
- **Dépendances** : aucune nouvelle dépendance Python ou JS (Flask et Pillow déjà présents, `base64` et `hashlib` en stdlib).
- **Sécurité** : mêmes mitigations que `/api/convert` (bind 127.0.0.1, allow-list algos, validation basename, validation params contre `PARAMS`). L'endpoint preview ne touche ni `outputs/` ni `history.json`, donc surface d'attaque plus petite.
- **Performance** : cache LRU des préfixes de pipeline (max 32 entrées), évite les recalculs sur les étapes figées. Downscale 256 px réduit le coût d'un facteur ~16× sur une image 1024². Cancellation client-only (V1) : les threads serveur vont au bout mais leurs résultats sont ignorés — acceptable pour usage solo localhost.
- **Pas de migration de données** : aucun format modifié, aucun fichier généré, `history.json` et `outputs/` strictement intouchés par le preview.
- **Compatibilité descendante** : le toggle est opt-in. Désactivé (par défaut), le comportement du dashboard est strictement identique à aujourd'hui.
