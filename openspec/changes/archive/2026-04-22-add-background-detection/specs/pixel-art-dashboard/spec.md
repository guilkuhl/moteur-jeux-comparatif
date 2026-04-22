## ADDED Requirements

### Requirement: Le panneau Convertir SHALL exposer un bouton `🎯 Détecter fond` et un toggle `Préserver le fond`

Le panneau `.convert-panel` MUST inclure :

- Un bouton `🎯 Détecter fond` qui, au clic, déclenche `GET /api/bgmask?image=<activeImage>` avec la valeur courante de `tolerance` (défaut 8), et affiche une overlay semi-transparente (`opacity: 0.5`) du masque retourné, par-dessus l'image source dans la zone de comparaison.
- Un toggle checkbox `[ ] Préserver le fond` qui, quand activé, ajoute `preserve_bg: true` aux params de chaque étape compatible (`denoise/*`, `sharpen/*`) lors de l'appel à `/api/preview` et `/api/convert`.
- Un petit champ numérique `tolerance` (0-50, défaut 8) exposé à côté du bouton pour ajuster la sensibilité de la détection.

Le bouton et le toggle MUST être désactivés (grisés) si aucune image n'est active (`activeImage === null`).

#### Scenario: Clic sur Détecter fond avec image active

- **GIVEN** une image active sélectionnée dans la sidebar
- **WHEN** l'utilisateur clique sur `🎯 Détecter fond`
- **THEN** le dashboard SHALL émettre `GET /api/bgmask?image=<basename>&tolerance=<val>`, afficher le PNG retourné en overlay sur l'image source avec `opacity: 0.5`, et afficher un label "Fond détecté: #RRGGBB" (ou "Fond non détecté") sous le bouton

#### Scenario: Toggle Préserver le fond modifie le payload preview

- **GIVEN** le toggle `Préserver le fond` activé et un pipeline `[{denoise, median}, {sharpen, unsharp_mask}]`
- **WHEN** le dashboard émet un `POST /api/preview`
- **THEN** le payload SHALL contenir `preserve_bg: true` dans les `params` de chaque étape

#### Scenario: Toggle désactivé n'ajoute pas preserve_bg

- **GIVEN** le toggle `Préserver le fond` désactivé (défaut)
- **WHEN** le dashboard émet un `POST /api/preview` ou `/api/convert`
- **THEN** le payload SHALL NE PAS contenir `preserve_bg` dans les `params` (ou contenir `preserve_bg: false`)

#### Scenario: Bouton désactivé sans image active

- **GIVEN** aucune image active sélectionnée
- **WHEN** on inspecte l'UI
- **THEN** le bouton `🎯 Détecter fond` SHALL être `disabled` et le toggle `Préserver le fond` SHALL être `disabled` avec un tooltip « Sélectionne une image d'abord »

### Requirement: L'overlay du masque SHALL être toggleable et non intrusive

L'overlay affichée après clic sur `🎯 Détecter fond` MUST :

- Être superposée à l'image source (côté gauche du comparateur) avec `opacity: 0.5`.
- Se retirer quand on re-clique sur `🎯 Détecter fond` (toggle on/off) ou quand l'image active change.
- Ne pas bloquer les interactions du comparateur (pan, zoom, drag du divider restent fonctionnels).
- Ne pas s'afficher dans le résultat officiel `/api/convert` (uniquement visualisation).

#### Scenario: Re-clic retire l'overlay

- **GIVEN** une overlay de masque affichée
- **WHEN** l'utilisateur clique à nouveau sur `🎯 Détecter fond`
- **THEN** l'overlay SHALL disparaître et l'image source SHALL redevenir seule

#### Scenario: Changement d'image active retire l'overlay

- **GIVEN** une overlay affichée pour `sprite1.png`
- **WHEN** l'utilisateur clique sur `sprite2.png` dans la sidebar
- **THEN** l'overlay SHALL être retirée automatiquement (l'utilisateur doit re-cliquer sur Détecter fond pour la nouvelle image)
