## 1. Logique auto-adapt dans drawPixelGrid

- [ ] 1.1 Dans `drawPixelGrid()`, remplacer le check `pixelScreen < 2 → hide` par une boucle : `stepEff = stepUser`, tant que `stepEff × scale < 2` et `stepEff ≤ 32`, faire `stepEff *= 2`
- [ ] 1.2 Si `stepEff × scale < 2` après la boucle (cas extrême), masquer et afficher warning
- [ ] 1.3 Sinon dessiner les lignes à `pixelScreen = stepEff × scale` (remplacer l'usage de `gridStep` par `stepEff` dans les boucles de dessin)
- [ ] 1.4 Les lignes majeures restent tous les 8 `stepEff`

## 2. Label step effectif dans la toolbar

- [ ] 2.1 Ajouter `<span id="grid-step-label">` dans `.cmp-toolbar`, juste après `#grid-step`, avec CSS `display: none` par défaut
- [ ] 2.2 CSS : `#grid-step-label.visible { display: inline-block; } #grid-step-label.adapted { font-style: italic; color: var(--muted); }`
- [ ] 2.3 Dans `drawPixelGrid()` après le calcul de `stepEff`, mettre à jour le label :
      - Si toggle OFF → masquer
      - Si stepEff === stepUser → `step N`, sans class `adapted`
      - Si stepEff !== stepUser → `step N→M`, class `adapted`, tooltip "Grille auto-adaptée : zoome pour descendre au step demandé"
- [ ] 2.4 Dans `refreshGridBtn()`, masquer aussi `#grid-step-label` quand la grille est OFF

## 3. Préserver valeur utilisateur

- [ ] 3.1 Vérifier que `gridStep` (variable interne) continue de refléter `stepUser`, pas `stepEff`
- [ ] 3.2 Vérifier que `localStorage.dashGridStep` et `#grid-step.value` ne sont JAMAIS modifiés par le rendu auto-adapté
- [ ] 3.3 Tests : saisir step=1, zoomer out, zoomer in, vérifier que l'input reste à "1"

## 4. Tests visuels

- [ ] 4.1 Image 1254×1254, step=1, viewport 1920 → scale ≈ 0.67, pixelScreen=0.67 < 2 → auto-adapt vers step=4 (pixelScreen=2.68). Label "step 1→4" visible en italique
- [ ] 4.2 Zoom ×2 sur la même image → scale=1.34, stepEff=2 (pixelScreen=2.68). Label "step 1→2"
- [ ] 4.3 Zoom ×3 → scale=2, stepEff=1 (pixelScreen=2). Label "step 1" (pas d'adaptation)
- [ ] 4.4 Image très grande, zoom faible tel que même step=64 ne suffit pas → warning ⚠ visible
- [ ] 4.5 `#grid-step` reste à "1" même quand auto-adapt bumpe à 4 ou 8

## 5. Validation capability

- [ ] 5.1 `openspec validate add-pixel-grid-auto-adapt` OK
- [ ] 5.2 `openspec archive add-pixel-grid-auto-adapt` applique le delta MODIFIED + ADDED
