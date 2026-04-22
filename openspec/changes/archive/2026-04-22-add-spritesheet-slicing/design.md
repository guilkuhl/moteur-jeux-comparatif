## Context

Les overrides sur une grille régulière demandent un modèle de données simple : une grille de base (cols, rows, cellW, cellH, gapX, gapY, marginX, marginY) plus une liste sparse de cellules modifiées.

```json
{
  "slicing": {
    "base": { "cols": 8, "rows": 4, "cellW": 16, "cellH": 16, "gapX": 0, "gapY": 0, "marginX": 0, "marginY": 0 },
    "overrides": [
      { "cellX": 2, "cellY": 1, "type": "resize", "w": 32, "h": 32 },
      { "cellX": 5, "cellY": 0, "type": "merge", "w": 2, "h": 1 },
      { "cellX": 7, "cellY": 3, "type": "ignore" },
      { "cellX": 0, "cellY": 0, "type": "name", "name": "hero_idle_01" }
    ]
  }
}
```

## Goals / Non-Goals

**Goals:**
- Édition visuelle : voir la grille, cliquer une cellule, modifier.
- Persistance par image dans `history.json`.
- Overrides de types : resize, merge, ignore, name.
- Compat avec pixel-grid-overlay existant (les deux coexistent visuellement).

**Non-Goals:**
- Drag-and-drop pour redimensionner au curseur (overkill).
- Éditeur non-rectangulaire (polygones).
- Export dans ce change — voir `spritesheet-export`.

## Decisions

**Décision 1 — Deux canvas distincts.**
- `#slicing-overlay` : grille + numéros + bbox survol.
- `#grid-overlay` existant : grille pixel pure (conservée tel quel).

Les deux peuvent être activés simultanément. `#slicing-overlay` a priorité z-index plus haut.

**Décision 2 — Mode édition vs mode lecture.**
En mode lecture (par défaut), la grille est affichée mais non interactive. En cliquant `Éditer cellules…`, on bascule en mode édition où :
- Le curseur devient crosshair.
- Clic sur une cellule ouvre un popover avec les 4 options.
- Esc sort du mode édition.

**Décision 3 — Numérotation des cellules.**
Un badge `col,row` (ex. `3,2`) dessiné à l'angle supérieur gauche de chaque cellule, font 10 px, couleur `#7c6fef`. Le nom custom override remplace le badge si défini.

**Décision 4 — Surbrillance bbox.**
Au hover d'une cellule : overlay jaune `rgba(255,224,96,0.2)` sur toute la cellule + bordure 2 px. Annule au mouseleave. Utilisé aussi lors de la validation des contraintes (remplace jaune par rouge).

**Décision 5 — Persistance.**
- `history.json` gagne une clé `slicing` par image (comme `runs`).
- Sauvegardée via `PUT /api/slicing/<basename>` avec validation côté serveur.
- `GET /api/slicing/<basename>` renvoie la config ou `{base: null, overrides: []}` si absente.
- Le dashboard demande la config au `selectImage()` et met à jour l'overlay.

## Risks / Trade-offs

- **Risque** : un override `merge` peut chevaucher un autre → configuration invalide.
  **Mitigation** : serveur rejette la config si chevauchement détecté, toast utilisateur.

- **Risque** : grille très dense (100×100) → overlay lent à rendre.
  **Mitigation** : limiter cols/rows à 256 chacun, warning au-delà.

## Open Questions

- Le nom custom est-il seulement utilisé à l'export, ou aussi visible dans l'UI ? → Les deux. Le badge numérique devient le nom si défini.
