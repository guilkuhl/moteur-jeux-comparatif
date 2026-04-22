## Context

Après slicing, on dispose d'une liste de cellules `{cellX, cellY, name, w, h}`. Les outils de cleanup opèrent sur cette liste (sans modifier l'image d'origine) et produisent soit des overrides (ignore, name renamings), soit une nouvelle image corrigée (normalize).

## Goals / Non-Goals

**Goals:**
- Réordonner l'ordre logique (pour animation ou export) sans toucher à la grille physique.
- Détecter automatiquement doublons et décalages, laisser l'utilisateur valider.
- Rapport unique pour archivage / debug.

**Non-Goals:**
- Réarranger physiquement les pixels du spritesheet (on passe par l'export pour ça).
- IA / ML pour classification de frames (hors scope).
- Édition pixel-par-pixel (out of scope).

## Decisions

**Décision 1 — Ordre logique via `order` override.**
Ajout d'un override additionnel `{cellX, cellY, type:"order", value: N}`. Si défini, l'export itère les cellules par `order` ASC au lieu de `row-major`. Permet drag-drop sans toucher à la grille.

**Décision 2 — Détection doublons via perceptual hash.**
Calcul `phash` 8×8 DCT par cellule (stdlib via pillow + numpy). Seuil Hamming ≤ 5 bits → considéré doublon. L'utilisateur valide dans une modal listant les paires suspectes, puis :
- Ou bien marque les doublons comme `ignore`.
- Ou bien leur attribue un alias (même nom, pour réutilisation dans le moteur).

**Décision 3 — Détection sous-pixel via phase correlation.**
Pour chaque cellule, comparer avec la cellule précédente dans l'ordre logique via FFT 2D + phase correlation → peak position = décalage en pixels. Si |Δx| ou |Δy| entre 0.2 et 2.5 px → suspicion sous-pixel. Propose recalage entier (round) ou interpolation (resample).

**Décision 4 — Normalisation taille uniforme.**
Détecter `maxW, maxH` parmi toutes les cellules non-ignorées. Si plusieurs tailles existent, proposer :
- Padder toutes les cellules à `maxW × maxH` (centré ou aligné).
- Produire un nouveau spritesheet avec toutes cellules uniformes.

Cette opération génère une nouvelle iter (comme constraints/apply).

**Décision 5 — Rapport structuré.**
`GET /api/cleanup/report?image=<basename>` renvoie :
```json
{
  "duplicates": [{"pair": [[x1,y1], [x2,y2]], "hamming": 3}],
  "subpixel_shifts": [{"cell":[x,y], "delta": [0.7, 1.2]}],
  "size_variants": {"unique_sizes": [[16,16],[17,16]], "dominant": [16,16]},
  "empty_cells": [[7,3]],
  "constraint_violations": [...]
}
```
Exportable en JSON via bouton `Exporter rapport`.

## Risks / Trade-offs

- **Risque** : perceptual hash 8×8 trop grossier → faux positifs.
  **Mitigation** : seuil conservateur (≤ 5 bits), l'utilisateur valide toujours manuellement.

- **Risque** : détection sous-pixel coûteuse sur grande grille.
  **Mitigation** : FFT par cellule ≈ 1 ms, négligeable pour < 1000 cellules.

## Open Questions

- Faut-il offrir un "auto-clean all" qui enchaîne tous les outils ? → Non pour v1, l'utilisateur valide chaque étape.
