# auto-tile-generation Specification

## Purpose
TBD - created by archiving change add-auto-tile-generation. Update Purpose after archive.
## Requirements
### Requirement: Le dashboard doit exposer un panneau Auto-tile avec 3 modes

Le dashboard MUST inclure un panneau `.autotile-panel` contenant :
- `<select>` mode : `wang16`, `wang47`, `wang256`.
- Sélecteur de tile `base` (cellule du spritesheet OU upload).
- Sélecteur de tile `bord`.
- Sélecteurs additionnels `coin extérieur`, `coin intérieur` (visibles uniquement pour wang47/wang256).
- Slider `Taille de tile` : `8`, `16`, `32`, `64` px.
- Bouton `Générer` qui appelle `POST /api/autotile/generate`.

#### Scenario: Panneau et sélection mode

- **WHEN** l'utilisateur sélectionne `wang47` dans le mode
- **THEN** les sélecteurs `coin extérieur` et `coin intérieur` SHALL devenir visibles, et le bouton `Générer` SHALL rester `disabled` tant que toutes les tiles requises ne sont pas définies

### Requirement: Le serveur doit générer un spritesheet auto-tile selon le mode choisi

Le backend MUST exposer `POST /api/autotile/generate` qui accepte `{mode, tiles: {base, edge, ...}, tile_size}` et retourne `{iterPath, gridLayout}`. Le serveur :

1. Charge les tiles d'entrée.
2. Pour chaque variant du mode (16 / 47 / 256), compose la tile finale par quadrants selon le bit-pattern.
3. Assemble dans une grille (4×4 / 7×7 / 16×16).
4. Sauvegarde comme nouvelle iter `iter_NNN_autotile_<mode>.png`.

#### Scenario: Wang 16 nominal

- **GIVEN** une `base` 16×16 et un `bord` 16×16
- **WHEN** `POST /api/autotile/generate` est appelé avec `mode=wang16, tile_size=16`
- **THEN** une nouvelle iter SHALL être créée contenant un spritesheet 64×64 (4×4 tiles de 16 px), chaque variant correspondant à son bit-pattern

#### Scenario: Wang 47 layout 7×7 avec ignored cells

- **GIVEN** les 5 tiles requises
- **WHEN** `POST /api/autotile/generate` est appelé avec `mode=wang47`
- **THEN** la nouvelle iter SHALL être un 7×7 avec 47 cellules valides et 2 cellules vides (transparentes), et la réponse SHALL inclure `gridLayout` indiquant les positions valides

### Requirement: Les tiles atomiques d'entrée doivent pouvoir provenir d'une cellule du spritesheet courant ou d'un upload séparé

Chaque sélecteur de tile MUST proposer 2 onglets :
- `Depuis le spritesheet courant` : sélection d'une cellule via clic dans le comparateur.
- `Upload fichier` : drag-drop d'un PNG/WebP de la taille `tile_size`.

Les tiles uploadées sont gardées en mémoire client (pas de persistance) jusqu'au clic `Générer`.

#### Scenario: Sélection depuis cellule

- **GIVEN** un spritesheet actif avec slicing défini
- **WHEN** l'utilisateur clique sur la cellule (2,1) en mode sélection auto-tile
- **THEN** la tile sélectionnée SHALL être affectée à l'input courant et un preview miniature SHALL apparaître dans le panneau

#### Scenario: Upload externe

- **GIVEN** un fichier PNG 16×16 dans le système de fichiers
- **WHEN** l'utilisateur drag-drop sur un sélecteur de tile
- **THEN** la tile SHALL être chargée et affichée en preview, sans persistance dans `inputs/`

