## 1. Modèle de données et backend

- [ ] 1.1 Ajouter la clé `slicing: {base, overrides}` dans le schéma de `history.json` (documenté dans le code)
- [ ] 1.2 Implémenter `GET /api/slicing/<basename>` : lire `history.json`, retourner la section slicing ou un défaut
- [ ] 1.3 Implémenter `PUT /api/slicing/<basename>` : parser le JSON body, valider (cols/rows bornés, pas de chevauchement, cellules dans grille), écrire atomiquement
- [ ] 1.4 Helper `validate_slicing_config(base, overrides)` qui retourne `[errors]`

## 2. Panneau UI

- [ ] 2.1 Ajouter `.slicing-panel` dans la sidebar (ou en nouveau panneau collapsible)
- [ ] 2.2 8 contrôles : cols, rows, cellW, cellH, gapX, gapY, marginX, marginY
- [ ] 2.3 Bouton `Appliquer` → PUT + refresh overlay
- [ ] 2.4 Bouton `Éditer cellules…` toggle mode édition
- [ ] 2.5 Au `selectImage()`, appeler `GET /api/slicing/<basename>` et peupler les champs

## 3. Canvas slicing-overlay

- [ ] 3.1 Ajouter `<canvas id="slicing-overlay">` dans `cmp-zoom-layer` (z-index entre grid-overlay et cmp-overlay)
- [ ] 3.2 Fonction `drawSlicingOverlay()` qui dessine : bordures cellules, badges col,row (ou nom custom), diagonale barrée pour cellules `ignore`
- [ ] 3.3 Listener `mousemove` pour surbrillance bbox jaune
- [ ] 3.4 Hook sur resize/zoom/scroll pour redessiner

## 4. Mode édition + popover override

- [ ] 4.1 Variable `slicingEditMode` booléenne
- [ ] 4.2 Au clic en mode édition, calculer la cellule à partir des coords souris
- [ ] 4.3 Ouvrir un popover positionné sur la cellule avec 4 boutons : Redimensionner / Fusionner / Ignorer / Nommer
- [ ] 4.4 Chaque bouton ouvre sa propre mini-modal pour saisir les params, puis ajoute l'override à la config locale
- [ ] 4.5 Sortie du mode via `Esc` ou re-clic du bouton `Éditer cellules…`

## 5. Tests

- [ ] 5.1 Grille 8×4 appliquée, overlay montre 32 cellules numérotées
- [ ] 5.2 Ajouter override `name` → badge remplacé par le nom
- [ ] 5.3 Ajouter override `ignore` → cellule barrée grise
- [ ] 5.4 Ajouter override `merge` 2×1 → les deux cellules fusionnent visuellement en une seule bordure
- [ ] 5.5 Tentative de chevauchement via PUT → rejeté 400 côté serveur
- [ ] 5.6 Reload page, config restaurée depuis history.json
