## ADDED Requirements

### Requirement: Le dashboard SHALL utiliser un layout 2 colonnes plein écran avec comparateur plein hauteur

La page principale `pixel-lab/dashboard/index.html` MUST s'afficher en CSS Grid avec 3 colonnes :

- Colonne gauche : largeur variable `--left-w` (défaut 280 px), 0 px si rétractée.
- Colonne centrale : `1fr` (occupe tout l'espace restant).
- Colonne droite (panneau Historique) : largeur variable `--right-w` (défaut 0 px fermée, 320 px ouverte).

La hauteur totale MUST être exactement `100vh` (pas de scroll vertical global). Chaque colonne MUST scroller individuellement si son contenu dépasse.

La colonne centrale MUST contenir uniquement le comparateur slider qui occupe 100% de sa largeur et 100% de sa hauteur.

#### Scenario: Layout 2 colonnes au chargement

- **GIVEN** le dashboard fraîchement chargé sur un écran 1920×1080
- **WHEN** on inspecte la page
- **THEN** la hauteur totale du `body` SHALL être exactement 1080 px, la sidebar gauche SHALL mesurer 280 px, la zone centrale SHALL occuper les ~1640 px restants en largeur et 1080 px en hauteur, et aucun scroll vertical global ne SHALL être présent

#### Scenario: Le comparateur remplit la colonne centrale

- **GIVEN** une image active sélectionnée
- **WHEN** on inspecte la zone comparateur
- **THEN** elle SHALL occuper 100% de la largeur et 100% de la hauteur de la colonne centrale (moins une toolbar overlay optionnelle de ~40 px en haut)

### Requirement: Le dashboard SHALL permettre la rétractation de la sidebar gauche et du panneau historique

Deux chevrons-toggle MUST être présents :

- Bouton `<` en bord droit de la sidebar gauche : toggle ouvre/ferme la sidebar (0 px ↔ 280 px).
- Bouton `>` en bord gauche du panneau droit ou un bouton dédié dans la sidebar : toggle ouvre/ferme le panneau Historique (0 px ↔ 320 px).

La transition de largeur MUST être animée (`transition: grid-template-columns 0.22s ease`).

L'état rétracté/ouvert MUST être persisté dans `localStorage` sous les clés `dashLeftOpen` et `dashRightOpen`, et restauré au prochain chargement.

#### Scenario: Rétractation de la sidebar

- **GIVEN** la sidebar gauche ouverte à 280 px
- **WHEN** l'utilisateur clique sur le chevron `<`
- **THEN** la sidebar SHALL se réduire à 0 px en 220 ms, le comparateur SHALL s'étendre pour occuper l'espace libéré, et `localStorage.dashLeftOpen` SHALL valoir `"false"`

#### Scenario: Persistance entre sessions

- **GIVEN** la sidebar gauche fermée et `localStorage.dashLeftOpen === "false"`
- **WHEN** l'utilisateur recharge la page
- **THEN** la sidebar SHALL rester fermée au chargement initial (pas de flash d'ouverture)

#### Scenario: Raccourci clavier pour le panneau Historique

- **GIVEN** le panneau Historique fermé
- **WHEN** l'utilisateur appuie sur la touche `H`
- **THEN** le panneau SHALL s'ouvrir avec la grille d'iters, et `localStorage.dashRightOpen` SHALL valoir `"true"`

### Requirement: Le panneau Convertir SHALL être intégré dans la sidebar gauche (pas dans une zone séparée)

Le panneau Convertir actuel (builder pipeline, toggles live/fullres/preserve_bg, bouton Lancer, indicateur status, live row) MUST être positionné dans la sidebar gauche, sous la liste d'images, avec :

- `flex: 0 0 auto` (ne prend que sa taille naturelle).
- `max-height: 60vh` avec `overflow-y: auto` (scroll interne si contenu trop long).
- Layout des `.step-row` en `flex-direction: column` ou grille compacte pour s'adapter à la largeur de 280 px.

La liste d'images au-dessus MUST avoir `flex: 1 1 auto` et `overflow-y: auto` (scroll interne).

#### Scenario: Builder pipeline compact dans la sidebar

- **GIVEN** la sidebar gauche de 280 px avec le panneau Convertir visible
- **WHEN** on ajoute une étape au pipeline
- **THEN** l'étape SHALL s'afficher sans déborder horizontalement, les selects algo/method SHALL s'empiler verticalement si nécessaire, et les boutons d'action (↑ ↓ ×) SHALL rester visibles

#### Scenario: Liste d'images scrollable sans affecter le panneau Convertir

- **GIVEN** 50 images dans la sidebar
- **WHEN** l'utilisateur scrolle dans la liste d'images
- **THEN** seule la liste SHALL défiler ; le panneau Convertir SHALL rester visible et fixe en bas de la sidebar

### Requirement: La grille d'iters SHALL être déplacée dans un panneau Historique rétractable à droite

La zone actuelle affichant la grille d'iters + la barre de tri/filtre MUST être retirée de la zone principale et placée dans un panneau rétractable à droite (colonne 3 du grid).

Le panneau Historique MUST :

- Être fermé par défaut au premier chargement (avant `localStorage` persisté).
- S'ouvrir via un bouton dédié dans la sidebar gauche (`📜 Historique`) ou la touche `H`.
- Contenir : la barre tri/filtre en haut + la grille d'iters en dessous, scrollable.
- Un clic sur un iter dans le panneau MUST continuer à fonctionner (sélection comme compareRight, refresh du comparateur).

#### Scenario: Grille d'iters accessible via le panneau Historique

- **GIVEN** le panneau Historique fermé et une image active avec 20 iters
- **WHEN** l'utilisateur clique sur `📜 Historique` dans la sidebar
- **THEN** le panneau droit SHALL s'ouvrir à 320 px, afficher les 20 iters sous forme de grille (comme actuellement), et la barre tri/filtre SHALL être présente en haut

#### Scenario: Sélection d'un iter depuis le panneau

- **GIVEN** le panneau Historique ouvert
- **WHEN** l'utilisateur clique sur la vignette d'un iter
- **THEN** l'iter SHALL devenir le `compareRight` du comparateur central, qui SHALL afficher le diff source ↔ iter comme aujourd'hui

### Requirement: La poignée du slider SHALL être centrée dans le viewport visible, pas dans le body de l'image

La poignée (`#cmp-handle`) MUST calculer sa position verticale en fonction de la portion visible du comparateur dans le viewport :

- Au chargement, sur scroll (`window.scroll`), sur resize, et après chaque `applyDivider`, le top de la poignée MUST être recalculé via `(visibleTop + visibleBottom) / 2 - handleRadius` où `visibleTop = max(0, -rect.top)` et `visibleBottom = min(rect.height, viewportHeight - rect.top)`.

Dans le nouveau layout (comparateur = 100vh), cette formule donne toujours `top ≈ 50vh`, donc la poignée est toujours au centre de l'écran.

#### Scenario: Poignée au centre du viewport

- **GIVEN** un comparateur de 100vh avec une image grande (même plus grande que le viewport avec zoom)
- **WHEN** on inspecte la poignée
- **THEN** son centre vertical SHALL être à ~50vh de l'écran (au milieu visible)

#### Scenario: Poignée reste visible lors du scroll

- **GIVEN** un layout où une partie du comparateur dépasse verticalement (cas rare en nouveau layout mais possible)
- **WHEN** l'utilisateur scrolle
- **THEN** la poignée SHALL se repositionner dynamiquement pour rester au centre de la portion visible du comparateur

### Requirement: Le header global SHALL être retiré et son contenu intégré dans la sidebar gauche

Le header actuel (badge « ⚡ Pixel Lab », info serveur en ligne/hors ligne) MUST être retiré du haut de la page. Son contenu essentiel (badge + statut serveur compact) MUST être positionné en haut de la sidebar gauche (~50 px max, `flex: 0 0 auto`).

#### Scenario: Pas de header global

- **GIVEN** le dashboard chargé
- **WHEN** on inspecte la page
- **THEN** aucun élément `<header>` ni `.header` ne SHALL occuper la largeur totale en haut ; le badge version SHALL apparaître dans le haut de la sidebar gauche

### Requirement: Le comparateur SHALL afficher une toolbar minimale overlay en haut

En haut de la zone comparateur (colonne centrale), une barre semi-transparente MUST afficher :

- Le nom du sprite actif (gauche).
- Les labels Gauche/Droite si un iter ou preview est chargé.
- Les boutons zoom (−, zoom level, +, reset, toggle axes pixel) à droite.
- Le label de timing preview (« Calculé en Xms · cache=N ») si en mode live.

Styling : `position: absolute; top: 0; left: 0; right: 0; height: 40px; background: rgba(10,10,20,0.5); backdrop-filter: blur(8px); color: #fff`. Cette toolbar MUST NE PAS bloquer les interactions sur l'image en dessous (sauf sur les contrôles eux-mêmes).

#### Scenario: Toolbar overlay visible sans couper l'image

- **GIVEN** le comparateur plein écran
- **WHEN** on survole la toolbar
- **THEN** les boutons SHALL être cliquables, et l'image SHALL rester visible en transparence à travers le fond semi-transparent

#### Scenario: Zoom control depuis la toolbar

- **GIVEN** la toolbar affichée
- **WHEN** l'utilisateur clique sur le bouton `+`
- **THEN** le zoom SHALL augmenter (comme avec l'ancien footer), et le label de niveau de zoom SHALL se mettre à jour

## MODIFIED Requirements

### Requirement: La sidebar SHALL distinguer l'image active (preview) de la multi-sélection (batch)

La sidebar (colonne gauche du layout 2 colonnes) MUST gérer deux états d'image orthogonaux : **selected** (cases à cocher, alimente `/api/convert`) et **active** (un seul item à la fois, alimente `/api/preview`). Le clic sur la miniature ou le corps de l'item MUST mettre à jour `active` sans modifier `selected`. Un indicateur visuel distinct (contour, badge, ou couleur d'accent) MUST signaler l'image active, différent de l'état `selected`. Cet indicateur visuel actif MUST être visible quand le toggle "Live preview" est activé ; quand le toggle est désactivé, l'indicateur peut rester discret ou être masqué, au choix de l'implémentation.

La sidebar SHALL être positionnée dans la colonne gauche du nouveau layout 2 colonnes et SHALL scroller indépendamment du panneau Convertir via `overflow-y: auto` sur sa section images.

#### Scenario: Cliquer une miniature ne décoche pas les sélections batch

- **GIVEN** 3 images cochées pour un batch futur et une 4ᵉ image actuellement active
- **WHEN** l'utilisateur clique sur une 5ᵉ image (non cochée)
- **THEN** l'état `active` SHALL être déplacé sur la 5ᵉ image, les 3 premières images cochées SHALL rester cochées inchangées, et la 4ᵉ ex-active SHALL perdre sa marque visuelle active

#### Scenario: Image active indiquée visuellement en mode live

- **GIVEN** le toggle "Live preview" activé
- **WHEN** on inspecte la sidebar
- **THEN** exactement un item SHALL porter la marque visuelle "active" (ex. contour coloré ou badge), et cet item SHALL correspondre à la dernière miniature cliquée

#### Scenario: Scroll indépendant de la liste d'images

- **GIVEN** 50 images dans la sidebar et le panneau Convertir visible en dessous
- **WHEN** l'utilisateur scrolle la liste d'images
- **THEN** seule la liste SHALL défiler ; le panneau Convertir SHALL rester visible et ancré au bas de la sidebar
