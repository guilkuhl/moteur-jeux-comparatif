## ADDED Requirements

### Requirement: Overlay axes pixel sur le comparateur
Le dashboard SHALL afficher, quand activé, un overlay `<canvas>` superposé au comparateur dessinant deux axes fléchés verts représentant exactement 1×1 pixel natif à l'échelle de zoom courante.

#### Scenario: Axes dessinés à la bonne échelle
- **WHEN** le toggle "Axes pixel" est activé et l'image est affichée à zoom ×2
- **THEN** chaque axe mesure exactement `2 × (largeur_body / naturalWidth)` pixels à l'écran

#### Scenario: Axes mis à jour au zoom
- **WHEN** l'utilisateur scrolle pour zoomer dans le comparateur
- **THEN** les axes sont immédiatement redessinés à la nouvelle échelle sans délai visible

#### Scenario: Taille minimale visible
- **WHEN** 1 pixel natif représente moins de 4px écran
- **THEN** les axes sont affichés avec une longueur minimale de 4px pour rester lisibles

### Requirement: Toggle on/off des axes
Le système SHALL fournir un bouton dans le footer du comparateur pour activer/désactiver l'overlay axes pixel.

#### Scenario: Activation du toggle
- **WHEN** l'utilisateur clique sur le bouton "Axes pixel"
- **THEN** le canvas overlay apparaît avec les deux axes verts

#### Scenario: Désactivation du toggle
- **WHEN** l'utilisateur clique à nouveau sur le bouton actif
- **THEN** le canvas overlay est masqué, le comparateur retrouve son état normal

### Requirement: Axes fléchés en vert
Les axes SHALL être dessinés en vert (`#00ff88`), avec une flèche à l'extrémité, une épaisseur de 2px, et une origine au coin supérieur gauche de l'image visible.

#### Scenario: Apparence des axes
- **WHEN** l'overlay est visible
- **THEN** l'axe X pointe vers la droite (→) et l'axe Y pointe vers le bas (↓), tous deux de couleur `#00ff88`

#### Scenario: Labels des axes
- **WHEN** l'overlay est visible
- **THEN** un label "X" apparaît à l'extrémité de l'axe X et "Y" à l'extrémité de l'axe Y
