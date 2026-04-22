## Context

Le serveur Flask expose déjà `/api/inputs` (GET), `/api/outputs/<stem>/<filename>` (DELETE), `/api/outputs/<stem>` (DELETE). On étend ce surface API avec un upload (POST) et un delete d'image source (DELETE `/api/inputs/<basename>`). La logique de move-to-trash sera factorisée dans un helper réutilisable partagé avec le change `add-dashboard-ux-polish` (prune orphelins).

Le frontend utilise déjà `fetch` pour les appels API et a un pattern de modal fonctionnel quelque part dans le dashboard (à confirmer) — sinon on en crée une minimaliste ici, réutilisable plus tard.

## Goals / Non-Goals

**Goals:**
- Upload en un geste depuis le navigateur, sans quitter le dashboard.
- Suppression avec archivage (pas de perte définitive — récupérable depuis `inputs/_trash/` et `outputs/_trash/`).
- Feedback visuel systématique (halo drag, toast résultat, modal confirmation).
- Validation stricte côté client ET côté serveur (extension, taille, MIME).

**Non-Goals:**
- Upload multiple simultané (un fichier à la fois, itérer l'utilisateur).
- Déplacer / renommer une image existante.
- Restaurer depuis le trash via le dashboard (opération manuelle pour v1).
- Confirmer via Enter au clavier dans la modal (bonus, pas requis).

## Decisions

**Décision 1 — Extensions et taille autorisées.**
- Extensions : `.png`, `.webp`, `.jpg`, `.jpeg`.
- Taille max : 20 MB (cohérent avec un sprite pixel-art raisonnablement grand).
- Validation client (early reject) + serveur (sécurité).
- Le basename uploadé conserve le nom du fichier original (après sanitation : suppression des espaces en début/fin, substitution des caractères non `[A-Za-z0-9._\- ]` par `_`).
- Si le nom existe déjà dans `inputs/`, le serveur renvoie `409 Conflict` avec `{error: "exists", suggestion: "<name>-2.png"}` et le client re-tente avec le suggestion ou demande à l'utilisateur.

**Décision 2 — Move-to-trash plutôt que `os.remove`.**
Pour toute suppression (input ou output), on déplace vers un sous-dossier `_trash/<name>_<timestamp>/` au sein de `inputs/` ou `outputs/`. Le timestamp évite les collisions si l'utilisateur supprime deux fois un fichier homonyme.

Helper unique `move_to_trash(path: Path, trash_root: Path) -> Path` dans `pixel-lab/server/app.py` (ou dans un nouveau `pixel-lab/server/_trash.py`). Partagé avec le change `add-dashboard-ux-polish`.

**Décision 3 — UI drag-drop ciblée sur la sidebar.**
On écoute `dragenter / dragover / dragleave / drop` uniquement sur `.sidebar` (pas sur toute la page) pour éviter d'interférer avec d'autres interactions. Pendant un drag actif :
- `.sidebar` reçoit la classe `.dragging-over` (halo violet, border pointillée).
- Un overlay `<div id="drop-hint">` affiche « Dépose l'image ici ».

Au drop :
- Récupérer `e.dataTransfer.files[0]`.
- Valider extension + taille côté client (reject silencieux sinon, toast rouge).
- `POST /api/inputs` avec FormData.
- Sur succès, `loadHistory()` + activer la nouvelle image.

**Décision 4 — Menu contextuel `⋯` sur `.img-item`.**
Un petit bouton `⋯` (3 points verticaux) apparaît au hover de chaque `.img-item`, aligné à droite. Au clic, un petit menu popover s'ouvre avec une seule action pour v1 : `🗑 Supprimer`. L'ouverture d'un autre menu ferme celui-ci.

Le clic-droit natif sur `.img-item` ouvre ce même menu (accessibilité par défaut).

**Décision 5 — Modal de confirmation unique.**
Créer un composant modal réutilisable `showConfirmModal({title, message, confirmLabel, cancelLabel})` qui retourne une Promise. Utilisé pour :
- Confirmer suppression d'une image (« Supprimer X et 12 iter(s) associé(s) ? Archive récupérable dans outputs/_trash/ »).
- (Change `add-dashboard-ux-polish`) confirmer nettoyage orphelins.

## Risks / Trade-offs

- **Risque** : un utilisateur dépose un gros fichier (5000×5000, 50 MB avant compression) → lag / erreur serveur.
  **Mitigation** : 20 MB limite stricte client + serveur, toast explicite.

- **Risque** : drag-drop de plusieurs fichiers → seul le premier est uploadé, les autres perdus silencieusement.
  **Mitigation** : détecter `files.length > 1` et afficher un toast « Dépose un fichier à la fois pour l'instant » + rejeter le drop.

- **Risque** : suppression concurrente (deux onglets ouverts qui suppriment la même image simultanément) → 404 sur le second.
  **Mitigation** : 404 géré gracieusement (refresh automatique, l'entrée aura déjà disparu).

- **Risque** : `POST /api/inputs` ne respecte pas les limites Flask par défaut (`MAX_CONTENT_LENGTH`).
  **Mitigation** : fixer `app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024` explicitement, renvoyer 413 avec message clair si dépassé.

- **Trade-off** : move-to-trash prend de la place disque. Acceptable pour un outil de dev local, à revisiter si ça devient un souci.

## Open Questions

- Faut-il convertir automatiquement les JPG uploadés en PNG ? → Non pour v1, garder fidèle au format d'origine.
- Permettre le renommage ? → Non pour v1. On peut toujours supprimer + ré-uploader avec le bon nom.
