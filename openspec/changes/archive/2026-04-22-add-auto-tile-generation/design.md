## Context

Les variants Wang sont indexés par un masque de bits :
- **Wang 16** : 4 bits (1 par coin = haut-gauche, haut-droite, bas-gauche, bas-droite). 2⁴ = 16 combinaisons.
- **Wang 47 (blob)** : 8 bits (4 cardinaux + 4 diagonaux), mais seulement 47 valeurs distinctes après élimination des configurations impossibles (ex. diagonal présent sans cardinaux adjacents).
- **Wang 256** : 8 bits, toutes les 256 combinaisons (utile pour des tiles plus complexes type marching squares 2D).

Pour générer une variant, on compose 4 quadrants (pour Wang 16) ou plus (pour 47/256) à partir des tiles d'entrée selon le bit-pattern.

## Goals / Non-Goals

**Goals:**
- Génération en un clic : 16 / 47 / 256 tiles à partir de 2-4 tiles atomiques.
- Sortie compatible Tiled (`.tsx`) — optionnel via un export futur.
- Preview avant génération (montrer 4-8 variants typiques).

**Non-Goals:**
- Génération à partir d'une seule tile (hand-painted, pas notre rôle).
- Edition pixel-perfect des variants générés (l'utilisateur ré-importe et corrige manuellement si besoin).
- Animation des tiles (frames temporelles).

## Decisions

**Décision 1 — Composition par quadrant (Wang 16).**
Chaque tile finale est composée de 4 quadrants. Pour chaque coin, selon que le bit "voisin diagonal" est à 0 (= bord) ou 1 (= continuation), on choisit le quadrant correspondant dans la tile `base` ou `bord`.

```
Tile finale [ Q_TL | Q_TR ]
            [ Q_BL | Q_BR ]
```

Pour le quadrant `TL`, on regarde le bit BIT_TL :
- BIT_TL = 1 → on prend Q_TL de la tile `base`.
- BIT_TL = 0 → on prend Q_TL de la tile `bord` (avec orientation appropriée).

**Décision 2 — Layout du spritesheet de sortie.**
Wang 16 → grille 4×4. Wang 47 → grille 7×7 + entrées vides marquées `ignore`. Wang 256 → grille 16×16. L'ordre d'index suit la convention Tiled.

**Décision 3 — Tiles d'entrée.**
- Mode minimaliste : juste `base` et `bord` (Wang 16, qualité moyenne).
- Mode optimal : `base`, `bord_horizontal`, `bord_vertical`, `coin_extérieur`, `coin_intérieur` (Wang 47/256).
- Permettre un input `image source du spritesheet` + sélection des cellules pour les tiles atomiques.

**Décision 4 — Algorithme de blending.**
- Découpe de chaque tile d'entrée en quadrants (size/2 × size/2).
- Pour chaque variant, assembler les 4 quadrants selon le bit-pattern.
- Optionnel : appliquer un léger feathering (1-2 px de blur sur les bords inter-quadrants) pour adoucir les jonctions.

**Décision 5 — Sortie.**
Une nouvelle iter `iter_NNN_autotile_<mode>.png` dans `outputs/<stem>/` + une entrée history.json.

## Risks / Trade-offs

- **Risque** : qualité visuelle médiocre si les tiles d'entrée ne sont pas conçues pour un blending propre.
  **Mitigation** : warning UI « Pour de meilleurs résultats, utilise des tiles spécifiquement designées pour blending ».

- **Risque** : Wang 256 produit beaucoup de combinaisons rarement utilisées.
  **Mitigation** : recommander Wang 47 (blob) par défaut.

## Open Questions

- Faut-il exporter aussi un `.tsx` Tiled ? → Hors scope, à ouvrir comme follow-up.
- Support des tiles non-carrées (rectangulaires) ? → Non pour v1, force carré.
