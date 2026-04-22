## Why

Aujourd'hui, ajouter ou supprimer une image source demande de manipuler le filesystem à la main : copier un PNG dans `pixel-lab/inputs/`, ou supprimer un fichier + son dossier `outputs/<stem>/` à la main. Le dashboard n'offre aucun moyen direct de gérer les inputs. Pour fluidifier les sessions de comparaison, on veut deux gestes simples : **déposer une image sur la sidebar pour l'uploader** et **cliquer sur un bouton pour supprimer une image** avec son historique associé.

## What Changes

1. **Drag-drop upload** — glisser un fichier `.png`, `.webp`, `.jpg`/`.jpeg` sur la sidebar déclenche un `POST /api/inputs` multipart qui écrit le fichier dans `pixel-lab/inputs/`. La sidebar se rafraîchit automatiquement et active la nouvelle image.
2. **Bouton Supprimer dans la sidebar** — un menu contextuel `⋯` sur chaque `.img-item` expose une action `🗑 Supprimer`. Au clic, une modal de confirmation apparaît ; si confirmée, `DELETE /api/inputs/<basename>` retire le fichier source et archive (déplace vers `outputs/_trash/`) le dossier `outputs/<stem>/` associé s'il existe. L'entrée disparaît de la sidebar et de `history.json`.

Les deux actions touchent des données persistantes : upload crée un fichier, delete archive un dossier. Chaque opération est accompagnée d'un retour visuel (toast de succès, liste d'erreurs si partiels).

## Capabilities

### New Capabilities
<!-- aucune -->

### Modified Capabilities
- `pixel-art-dashboard`: ajout de 2 requirements (drag-drop upload + bouton supprimer) et 1 requirement serveur (route `POST /api/inputs` + `DELETE /api/inputs/<basename>`).

## Impact

- **Frontend (pixel-lab/dashboard/index.html)** :
  - Listeners `dragenter/dragover/drop` sur la sidebar.
  - Indicateur visuel pendant le drag (halo violet / message « Dépose ici »).
  - Validation côté client : extension dans `.png/.webp/.jpg/.jpeg`, taille max 20 MB.
  - Appel `fetch('/api/inputs', {method:'POST', body: FormData})`.
  - Menu contextuel `⋯` sur `.img-item` (ou clic-droit) avec action Supprimer.
  - Modal de confirmation réutilisable (même composant que pour les orphelins).
- **Backend (pixel-lab/server/app.py)** :
  - Nouvelle route `POST /api/inputs` multipart : valide MIME, écrit dans `pixel-lab/inputs/`, renvoie `{basename, size}`.
  - Nouvelle route `DELETE /api/inputs/<basename>` : déplace le fichier vers `inputs/_trash/` et archive `outputs/<stem>/` vers `outputs/_trash/` ; retire l'entrée de `history.json`.
- **Specs** : 3 nouveaux requirements dans `pixel-art-dashboard`.
- **Dépendance** : la route `POST /api/history/prune` du change `add-dashboard-ux-polish` est réutilisée pour la purge atomique d'une seule entrée (ou on mutualise la logique de move-to-trash dans un helper).
