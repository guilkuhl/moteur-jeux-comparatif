## 1. Helper move-to-trash partagé (backend)

- [ ] 1.1 Créer un helper `move_to_trash(src: Path, trash_root: Path) -> Path` qui garantit un timestamp unique et retourne le chemin de destination
- [ ] 1.2 Factoriser ce helper pour être réutilisé par le change `add-dashboard-ux-polish` (prune orphelins)
- [ ] 1.3 Tests unitaires : collision, source inexistante, dossier vs fichier

## 2. Route POST /api/inputs (upload)

- [ ] 2.1 Ajouter `MAX_CONTENT_LENGTH = 20 * 1024 * 1024` dans la config Flask
- [ ] 2.2 Implémenter la route `POST /api/inputs` acceptant `multipart/form-data` avec champ `file`
- [ ] 2.3 Valider l'extension (allowlist strict `.png/.webp/.jpg/.jpeg`)
- [ ] 2.4 Sanitize le basename (trim, remplacer caractères non alphanumériques+`._- `)
- [ ] 2.5 Si le fichier existe, générer une suggestion `<stem>-2<ext>` (ou `-3`, `-4`... jusqu'à trouver un libre) et renvoyer `409 {error, suggestion}`
- [ ] 2.6 Écrire le fichier, renvoyer `200 {basename, size}`
- [ ] 2.7 Gérer `413 Request Entity Too Large` avec message JSON clair

## 3. Route DELETE /api/inputs/<basename>

- [ ] 3.1 Implémenter la route DELETE qui :
      - `404` si le fichier n'existe pas
      - Déplace `inputs/<basename>` vers `inputs/_trash/` via le helper
      - Déplace `outputs/<stem>/` vers `outputs/_trash/` si présent
      - Retire l'entrée de `history.json` (atomic write via tempfile)
      - Renvoie `200 {archivedSource, archivedOutputs}`

## 4. UI drag-drop upload

- [ ] 4.1 Ajouter listeners `dragenter/dragover/dragleave/drop` sur `.sidebar`
- [ ] 4.2 Ajouter la classe CSS `.sidebar.dragging-over` avec halo violet et bordure pointillée
- [ ] 4.3 Injecter un overlay `<div id="drop-hint">Dépose l'image ici</div>` visible uniquement pendant le drag
- [ ] 4.4 Au drop : valider client (extension + taille), afficher toast rouge si reject
- [ ] 4.5 Rejeter drop de plusieurs fichiers (`files.length > 1`) avec toast explicite
- [ ] 4.6 Appeler `POST /api/inputs` avec FormData, gérer 200/409/413/5xx avec toast approprié
- [ ] 4.7 Sur succès : `loadHistory()`, activer la nouvelle image, toast vert

## 5. UI menu contextuel `⋯` + suppression

- [ ] 5.1 Ajouter un bouton `⋯` à droite de chaque `.img-item`, visible au hover
- [ ] 5.2 Au clic (ou clic-droit sur `.img-item`), ouvrir un popover contenant l'action `🗑 Supprimer`
- [ ] 5.3 Click outside du popover le ferme
- [ ] 5.4 Au clic sur `🗑 Supprimer`, appeler `showConfirmModal({...})` avec un message décrivant le nombre d'iters perdus
- [ ] 5.5 Si confirmé, appeler `DELETE /api/inputs/<basename>`, refresh sidebar, activer autre image si besoin, toast vert

## 6. Composant modal de confirmation réutilisable

- [ ] 6.1 Créer `<div id="confirm-modal">` masqué par défaut, contenant titre, message, deux boutons
- [ ] 6.2 Exposer `showConfirmModal({title, message, confirmLabel, cancelLabel}) -> Promise<boolean>`
- [ ] 6.3 Fermer sur `Escape`, confirmer sur `Enter` (bonus)
- [ ] 6.4 Mutualiser avec le change `add-dashboard-ux-polish` (même fonction)

## 7. Toast notifications

- [ ] 7.1 Créer un conteneur `<div id="toast-stack">` en position fixed bas-droite
- [ ] 7.2 Exposer `showToast(message, variant='info'|'success'|'error')` qui injecte un toast, auto-retrait après 4s
- [ ] 7.3 Styles CSS pour les 3 variantes

## 8. Tests visuels

- [ ] 8.1 Drag-drop d'un PNG → upload réussit, image active
- [ ] 8.2 Drag-drop d'un PDF → toast rouge, aucun appel
- [ ] 8.3 Drag-drop d'un PNG > 20 MB → toast rouge
- [ ] 8.4 Drag-drop d'un nom existant → 409, proposition de renommage
- [ ] 8.5 Clic `⋯` → `🗑 Supprimer` → modal → confirmer → image disparaît, dossiers `_trash` créés
- [ ] 8.6 Annuler dans la modal → aucune action
- [ ] 8.7 Clic-droit sur `.img-item` ouvre le même menu

## 9. Validation finale

- [ ] 9.1 `openspec validate add-dashboard-input-management` OK
- [ ] 9.2 Régression des autres features (live preview, builder, comparateur, etc.)
