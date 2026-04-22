## ADDED Requirements

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

Quand `pixelScreen = step × scale < 2` (ex. image dézoomée), le canvas SHALL être effacé et un petit warning discret (tooltip ou badge) SHALL s'afficher dans la toolbar indiquant « Grille masquée (zoom insuffisant) ».

#### Scenario: Grille automatiquement masquée

- **GIVEN** la grille active, pas = 1, et une image dézoomée à ×0.5 (`pixelScreen = 0.5`)
- **WHEN** on inspecte le canvas
- **THEN** aucune ligne ne SHALL être dessinée, et un indicateur visuel SHALL signaler « Grille masquée (zoom insuffisant) » à côté du toggle

### Requirement: Les lignes majeures SHALL être mises en évidence tous les 8 pas

Pour aider l'œil à compter, les lignes correspondant à un multiple de 8 fois le pas (index `i % 8 == 0`) SHALL être dessinées avec une opacité plus forte et une épaisseur légèrement supérieure. Les lignes normales utilisent `rgba(255,255,255,0.15)` lineWidth 1, les lignes majeures `rgba(255,255,255,0.3)` lineWidth 1.5.

#### Scenario: Lignes majeures visibles

- **GIVEN** une grille avec pas = 1 active
- **WHEN** on inspecte les lignes dessinées sur le canvas
- **THEN** une ligne sur 8 (aux indices 0, 8, 16, 24…) SHALL avoir une opacité et un lineWidth supérieurs aux autres

### Requirement: L'état du toggle et du pas doit être persisté dans localStorage

Le dashboard MUST persister l'état dans `localStorage` :

- `localStorage.dashGridOn` : `"true"` ou `"false"` (défaut `"false"`).
- `localStorage.dashGridStep` : `"1"` à `"64"` (défaut `"1"`).

Au chargement du dashboard, les valeurs persistées MUST être restaurées et la grille SHALL apparaître directement dans son état actif si `dashGridOn === "true"`, une fois `#cmp-left` rendu.

#### Scenario: Persistance toggle

- **GIVEN** la grille active et pas = 4
- **WHEN** l'utilisateur recharge la page
- **THEN** `dashGridOn === "true"` et `dashGridStep === "4"` après reload, et la grille SHALL être immédiatement visible dès que l'image source est chargée
