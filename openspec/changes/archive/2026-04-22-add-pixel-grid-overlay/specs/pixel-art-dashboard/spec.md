## ADDED Requirements

### Requirement: La toolbar du comparateur SHALL exposer un bouton `🔳 Grille` et son raccourci clavier `G`

La `.cmp-toolbar` overlay existante MUST inclure un bouton `🔳 Grille` (classe `.zbtn`) à côté du bouton `⊹ Axes pixel`. Le bouton toggle l'affichage de l'overlay `#grid-overlay` (capability `pixel-grid-overlay`).

Quand activé, le bouton MUST prendre la classe `.active`. La touche `G` sur le clavier (hors focus dans un champ `input/textarea/select`) MUST basculer le même toggle.

Quand le toggle est actif, un petit champ `<input type="number" id="grid-step">` (pas de la grille, 1..64) MUST apparaître dans la toolbar à droite immédiate du bouton. Le champ SHALL disparaître quand le toggle repasse à OFF.

#### Scenario: Clic sur le bouton Grille

- **GIVEN** la toolbar du comparateur visible
- **WHEN** l'utilisateur clique sur `🔳 Grille`
- **THEN** l'overlay `#grid-overlay` SHALL apparaître, le bouton SHALL prendre la classe `.active`, et le champ `#grid-step` SHALL être visible dans la toolbar avec la valeur courante du pas

#### Scenario: Raccourci clavier G

- **GIVEN** le dashboard avec le focus sur le comparateur (pas dans un input)
- **WHEN** l'utilisateur appuie sur la touche `G`
- **THEN** le toggle grille SHALL basculer (ON ↔ OFF) comme si le bouton avait été cliqué

#### Scenario: Raccourci G ignoré dans un champ

- **GIVEN** le focus sur `#bg-tolerance` (ou tout autre `input`)
- **WHEN** l'utilisateur tape `g` pour saisir du texte
- **THEN** le toggle grille ne SHALL PAS basculer, et la saisie SHALL fonctionner normalement
