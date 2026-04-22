## ADDED Requirements

### Requirement: La grille pixel doit exposer 3 contrôles de personnalisation visuelle

La toolbar du comparateur MUST inclure, à côté de `#grid-step-label`, 3 contrôles visibles uniquement quand le toggle grille est ON :

- `<input type="color" id="grid-color">` (défaut `#ffffff`).
- `<input type="range" id="grid-opacity" min="0.05" max="1" step="0.05">` (défaut `0.15`).
- `<select id="grid-blend">` avec options `difference` (défaut), `normal`, `multiply`.

Tout changement de l'un de ces contrôles MUST déclencher un redessin immédiat de la grille via `drawPixelGrid()`.

Les valeurs MUST être persistées dans `localStorage` :
- `dashGridColor` (string `#RRGGBB`).
- `dashGridOpacity` (string décimal entre 0.05 et 1).
- `dashGridBlend` (string).

#### Scenario: Changement de couleur

- **GIVEN** la grille active avec couleur par défaut blanc
- **WHEN** l'utilisateur sélectionne `#ff0000` dans `#grid-color`
- **THEN** la grille SHALL être redessinée avec des lignes rouges, et `localStorage.dashGridColor` SHALL valoir `"#ff0000"`

#### Scenario: Changement d'opacité

- **GIVEN** la grille active à opacité 0.15
- **WHEN** l'utilisateur déplace le slider à 0.5
- **THEN** la grille SHALL être redessinée avec des lignes plus visibles, et `localStorage.dashGridOpacity` SHALL valoir `"0.5"`

#### Scenario: Changement de blend mode

- **GIVEN** la grille active avec `mix-blend-mode: difference`
- **WHEN** l'utilisateur sélectionne `normal` dans le select
- **THEN** le canvas `#grid-overlay` SHALL recevoir `style.mixBlendMode = 'normal'`, et `localStorage.dashGridBlend` SHALL valoir `"normal"`

## MODIFIED Requirements

### Requirement: Les lignes majeures SHALL être mises en évidence tous les 8 pas

Pour aider l'œil à compter, les lignes correspondant à un multiple de 8 fois le pas effectif (index `i % 8 == 0`) SHALL être dessinées avec une **opacité doublée** par rapport aux lignes normales (clampée à 1.0) et une épaisseur légèrement supérieure (`lineWidth = 1.5` vs `1`).

Les couleurs normales et majeures utilisent la **couleur configurée** dans `#grid-color` (défaut `#ffffff`), avec :
- Lignes normales : `rgba(R, G, B, opacity)` où opacity vient de `#grid-opacity`.
- Lignes majeures : `rgba(R, G, B, min(1, opacity * 2))`.

#### Scenario: Lignes majeures visibles

- **GIVEN** une grille avec pas = 1 active, couleur blanc, opacité 0.15
- **WHEN** on inspecte les lignes dessinées sur le canvas
- **THEN** une ligne sur 8 (aux indices 0, 8, 16, 24…) SHALL être dessinée avec opacité 0.3 (= 0.15 × 2) et lineWidth 1.5, contre opacité 0.15 et lineWidth 1 pour les autres
