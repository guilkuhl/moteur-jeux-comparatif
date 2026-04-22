# pixel-grid-overlay Specification

## Purpose
TBD - created by archiving change add-pixel-grid-overlay. Update Purpose after archive.
## Requirements
### Requirement: Le comparateur SHALL proposer un overlay grille pixel toggleable

Le dashboard `pixel-lab/dashboard/index.html` MUST inclure un overlay `<canvas id="grid-overlay">` superposé à `#cmp-left` dans le comparateur central. Cet overlay est masqué (`display: none` ou équivalent) tant qu'il n'est pas activé. Une fois activé, il dessine une grille complète : lignes verticales et horizontales espacées d'exactement `N × scale` pixels écran, où `scale = cmp-left.offsetWidth / cmp-left.naturalWidth` et `N` est le pas courant (défaut 1).

Le canvas `#grid-overlay` MUST être positionné avec un z-index entre `#cmp-left` et `#cmp-overlay` pour ne pas bloquer les interactions du slider de comparaison.

#### Scenario: Grille visible au bon pas

- **GIVEN** une image source 256×256 affichée à zoom ×4 (soit 1024×1024 rendu), pas = 1
- **WHEN** le toggle grille est activé
- **THEN** le canvas `#grid-overlay` SHALL dessiner 256 lignes verticales et 256 lignes horizontales, espacées exactement de 4 pixels écran chacune, couvrant toute la surface visible de `#cmp-left`

#### Scenario: Pas personnalisé

- **GIVEN** la grille active avec pas = 8
- **WHEN** on inspecte les lignes
- **THEN** elles SHALL être espacées de `8 × scale` pixels écran (une ligne tous les 8 pixels natifs)

#### Scenario: Redessin au zoom

- **GIVEN** la grille active à zoom ×2
- **WHEN** l'utilisateur zoome à ×4
- **THEN** la grille SHALL être immédiatement redessinée avec un nouveau `pixelScreen = 4 × step`, sans délai visible

### Requirement: Le pas de la grille SHALL être configurable via un input numérique

La toolbar du comparateur MUST inclure un input numérique `<input type="number" min="1" max="64" value="1" id="grid-step">` à côté du bouton `🔳 Grille`. Cet input MUST être visible uniquement quand le toggle grille est actif. Le changement de valeur déclenche un redessin immédiat sans toucher à l'état du toggle.

#### Scenario: Changement de pas en direct

- **GIVEN** la grille active avec pas = 1
- **WHEN** l'utilisateur saisit 8 dans le champ pas
- **THEN** la grille SHALL se redessiner avec le nouveau pas, et `localStorage.dashGridStep` SHALL valoir `"8"`

#### Scenario: Bornes du pas

- **WHEN** l'utilisateur tente de saisir une valeur hors bornes (ex. 0 ou 100)
- **THEN** l'input SHALL clamper à `[1, 64]` et le redessin SHALL utiliser la valeur clampée

### Requirement: Si la grille devient illisible (case < 2px écran), elle SHALL ne pas être dessinée

Quand le step utilisateur produit `pixelScreen = stepUser × scale < 2` (ex. image dézoomée), le dashboard MUST d'abord tenter une **auto-adaptation** : trouver le plus petit exposant `n ≥ 0` tel que `stepEff = stepUser × 2ⁿ` satisfait `stepEff × scale ≥ 2`, avec `stepEff ≤ 64`. Si un tel `stepEff` existe, la grille SHALL être dessinée avec ce `stepEff` au lieu de `stepUser`. Si aucun `stepEff ≤ 64` ne satisfait le seuil, le canvas SHALL être effacé et un petit warning discret (tooltip ou badge) SHALL s'afficher dans la toolbar indiquant « Grille masquée (zoom insuffisant) ».

La valeur dans l'input `#grid-step` et dans `localStorage.dashGridStep` MUST rester strictement égale à `stepUser` (non mutée par l'auto-adaptation).

#### Scenario: Grille automatiquement masquée quand même stepEff=64 est insuffisant

- **GIVEN** la grille active, `stepUser = 1`, et une image dézoomée à `scale = 0.02` (`pixelScreen = 0.02` pour step 1, `pixelScreen = 1.28` pour step 64)
- **WHEN** on inspecte le canvas
- **THEN** aucune ligne ne SHALL être dessinée, et un indicateur visuel SHALL signaler « Grille masquée (zoom insuffisant) » à côté du toggle

#### Scenario: Auto-adaptation quand stepUser est trop petit

- **GIVEN** la grille active, `stepUser = 1`, et une image affichée avec `scale = 0.3` (`pixelScreen = 0.3` avec step 1, mais `pixelScreen = 2.4` avec step 8)
- **WHEN** on inspecte le canvas
- **THEN** la grille SHALL être dessinée avec `stepEff = 8` (lignes espacées de 2.4 px écran), la valeur `#grid-step.value` SHALL rester `"1"`, et `localStorage.dashGridStep` SHALL rester `"1"`

#### Scenario: Pas d'auto-adaptation quand stepUser suffit déjà

- **GIVEN** la grille active, `stepUser = 4`, et `scale = 1` (`pixelScreen = 4`)
- **WHEN** on inspecte les lignes
- **THEN** la grille SHALL être dessinée avec `stepEff = stepUser = 4`, sans auto-adaptation

### Requirement: Les lignes majeures SHALL être mises en évidence tous les 8 pas

Pour aider l'œil à compter, les lignes correspondant à un multiple de 8 fois le pas effectif (index `i % 8 == 0`) SHALL être dessinées avec une **opacité doublée** par rapport aux lignes normales (clampée à 1.0) et une épaisseur légèrement supérieure (`lineWidth = 1.5` vs `1`).

Les couleurs normales et majeures utilisent la **couleur configurée** dans `#grid-color` (défaut `#ffffff`), avec :
- Lignes normales : `rgba(R, G, B, opacity)` où opacity vient de `#grid-opacity`.
- Lignes majeures : `rgba(R, G, B, min(1, opacity * 2))`.

#### Scenario: Lignes majeures visibles

- **GIVEN** une grille avec pas = 1 active, couleur blanc, opacité 0.15
- **WHEN** on inspecte les lignes dessinées sur le canvas
- **THEN** une ligne sur 8 (aux indices 0, 8, 16, 24…) SHALL être dessinée avec opacité 0.3 (= 0.15 × 2) et lineWidth 1.5, contre opacité 0.15 et lineWidth 1 pour les autres

### Requirement: L'état du toggle et du pas doit être persisté dans localStorage

Le dashboard MUST persister l'état dans `localStorage` :

- `localStorage.dashGridOn` : `"true"` ou `"false"` (défaut `"false"`).
- `localStorage.dashGridStep` : `"1"` à `"64"` (défaut `"1"`).

Au chargement du dashboard, les valeurs persistées MUST être restaurées et la grille SHALL apparaître directement dans son état actif si `dashGridOn === "true"`, une fois `#cmp-left` rendu.

#### Scenario: Persistance toggle

- **GIVEN** la grille active et pas = 4
- **WHEN** l'utilisateur recharge la page
- **THEN** `dashGridOn === "true"` et `dashGridStep === "4"` après reload, et la grille SHALL être immédiatement visible dès que l'image source est chargée

### Requirement: La toolbar doit afficher le step effectif quand il diffère du step utilisateur

Le dashboard MUST afficher un label compact `#grid-step-label` dans la toolbar du comparateur, à côté de `#grid-step`. Ce label MUST :

- Être masqué quand le toggle grille est OFF.
- Afficher `step X` quand `stepEff === stepUser`.
- Afficher `step X→Y` quand `stepEff !== stepUser` (où X = stepUser, Y = stepEff), avec un tooltip expliquant « Grille auto-adaptée : zoome pour descendre au step demandé ».

#### Scenario: Label sans auto-adaptation

- **GIVEN** stepUser = 4 et stepEff = 4 (scale suffisant)
- **WHEN** on inspecte `#grid-step-label`
- **THEN** il SHALL afficher `step 4` (sans flèche) et SHALL ne PAS avoir de tooltip indiquant un fallback

#### Scenario: Label avec auto-adaptation

- **GIVEN** stepUser = 1 et stepEff = 8 (auto-adapt déclenchée)
- **WHEN** on inspecte `#grid-step-label`
- **THEN** il SHALL afficher `step 1→8` avec un tooltip contenant « auto-adaptée » et le texte SHALL être stylistiquement distinct (italique, couleur atténuée, ou icône)

#### Scenario: Label masqué quand la grille est OFF

- **GIVEN** le toggle grille désactivé
- **WHEN** on inspecte `#grid-step-label`
- **THEN** il SHALL être masqué (`display: none` ou équivalent)

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

