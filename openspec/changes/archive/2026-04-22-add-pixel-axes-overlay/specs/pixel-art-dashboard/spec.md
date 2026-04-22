## ADDED Requirements

### Requirement: Bouton toggle axes pixel dans le footer comparateur
Le dashboard SHALL inclure un bouton "Axes pixel" dans le footer du comparateur, à côté des contrôles de zoom existants.

#### Scenario: Bouton visible dans le footer
- **WHEN** le comparateur est affiché avec deux images sélectionnées
- **THEN** un bouton "Axes pixel" est visible dans le footer du comparateur

#### Scenario: État actif du bouton
- **WHEN** le toggle est activé
- **THEN** le bouton apparaît avec le style `.active` (fond accent violet)
