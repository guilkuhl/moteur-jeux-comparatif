## MODIFIED Requirements

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

## ADDED Requirements

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
