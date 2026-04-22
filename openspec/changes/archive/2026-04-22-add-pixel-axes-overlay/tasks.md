## 1. Canvas overlay et toggle

- [x] 1.1 Ajouter le CSS `.pixel-axes-canvas` : `position:absolute; top:0; left:0; pointer-events:none; z-index:200`
- [x] 1.2 Injecter un `<canvas id="pixel-axes-canvas">` dans `.compare-body` au moment de `initSlider()`
- [x] 1.3 Ajouter la variable JS `let showPixelAxes = false`
- [x] 1.4 Ajouter le bouton "Axes pixel" dans le template `buildSliderHTML()` dans le footer, à côté des boutons zoom

## 2. Dessin des axes

- [x] 2.1 Implémenter `drawPixelAxes()` : récupérer `naturalWidth` de `#cmp-left`, calculer `pixelSize = cmpZ × (bodyWidth / naturalWidth)`, clamper à min 4px
- [x] 2.2 Calculer l'origine en tenant compte du pan (`cmpPx`, `cmpPy`) pour que les axes partent du coin supérieur gauche de l'image
- [x] 2.3 Dessiner l'axe X (→) en `#00ff88`, épaisseur 2px, avec tête de flèche triangulaire
- [x] 2.4 Dessiner l'axe Y (↓) en `#00ff88`, épaisseur 2px, avec tête de flèche triangulaire
- [x] 2.5 Ajouter les labels "X" et "Y" en vert à l'extrémité de chaque axe (font 11px)
- [x] 2.6 Appeler `drawPixelAxes()` depuis `applyCmpZoom()` si `showPixelAxes` est actif

## 3. Toggle et état

- [x] 3.1 Implémenter `togglePixelAxes()` : basculer `showPixelAxes`, mettre à jour la classe `.active` du bouton, afficher/masquer le canvas
- [x] 3.2 Réinitialiser le canvas (effacer + masquer) quand `initSlider()` est rappelé (changement d'image)
- [x] 3.3 Écouter l'événement `load` sur `#cmp-left` pour redessiner les axes si l'image change après activation
