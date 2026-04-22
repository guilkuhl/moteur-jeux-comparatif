## 1. Canvas overlay dans le DOM

- [ ] 1.1 Ajouter un `<canvas id="grid-overlay">` dans le conteneur comparateur (`main`), juste après `#cmp-left` et avant `#cmp-overlay`
- [ ] 1.2 Appliquer CSS `position: absolute; top: 0; left: 0; pointer-events: none; z-index: 10; mix-blend-mode: difference;`
- [ ] 1.3 Synchroniser la taille du canvas (`width` / `height` attributes) avec `#cmp-left.offsetWidth/offsetHeight` au chargement image, resize, et zoom

## 2. Bouton et input step dans la toolbar

- [ ] 2.1 Ajouter un bouton `<button class="zbtn" id="btn-grid" title="Afficher la grille pixel (G)">🔳</button>` dans `.cmp-toolbar`, entre le bouton `⊹` et l'extrémité droite
- [ ] 2.2 Ajouter `<input type="number" id="grid-step" min="1" max="64" value="1" hidden>` à droite du bouton, affiché uniquement quand le toggle est ON
- [ ] 2.3 Ajouter les handlers `onclick="toggleGrid()"` sur le bouton et `onchange="setGridStep(this.value)"` sur l'input

## 3. Rendu de la grille

- [ ] 3.1 Implémenter `drawPixelGrid()` qui : calcule `scale`, `pixelScreen = step * scale`, retourne tôt si `pixelScreen < 2`
- [ ] 3.2 Dessiner les lignes avec un seul `beginPath()` + boucle `moveTo/lineTo` + `stroke()`, distinguer les lignes majeures (multiples de 8) avec opacité et lineWidth plus forts
- [ ] 3.3 Brancher `drawPixelGrid` sur les events : `load` de `#cmp-left`, `resize` window, `scroll` window, et après chaque `applyZoom`
- [ ] 3.4 Quand `pixelScreen < 2`, afficher un badge `.grid-warning` dans la toolbar avec tooltip « Grille masquée (zoom insuffisant) »

## 4. Raccourci clavier G

- [ ] 4.1 Ajouter un listener `document.addEventListener('keydown', ...)` qui réagit à `key === 'g' || key === 'G'`
- [ ] 4.2 Ignorer si `document.activeElement` est un `INPUT`, `TEXTAREA` ou `SELECT`
- [ ] 4.3 Appeler `toggleGrid()` (déduplicage avec le handler du bouton)

## 5. Persistance localStorage

- [ ] 5.1 Au `DOMContentLoaded`, lire `dashGridOn` et `dashGridStep`, appliquer à `#btn-grid.classList`, `#grid-step.value`, et appeler `drawPixelGrid()` si `dashGridOn === "true"`
- [ ] 5.2 Dans `toggleGrid()`, écrire la nouvelle valeur dans `localStorage.dashGridOn`
- [ ] 5.3 Dans `setGridStep()`, clamper dans `[1,64]` puis écrire dans `localStorage.dashGridStep`, puis redessiner

## 6. Tests visuels

- [ ] 6.1 Grille visible à zoom ×4 avec pas=1, 256 lignes verticales et 256 horizontales espacées de 4px écran
- [ ] 6.2 Changement de pas 1 → 8 redessine la grille avec moins de lignes
- [ ] 6.3 Dézoom extrême déclenche le masquage auto avec badge warning visible
- [ ] 6.4 Raccourci G bascule le toggle, et ne l'interfère pas quand focus dans #bg-tolerance
- [ ] 6.5 Reload de la page avec dashGridOn=true restaure la grille immédiatement
- [ ] 6.6 Cohabitation avec le toggle Axes pixel : les deux overlays coexistent sans s'effacer mutuellement

## 7. Validation capability

- [ ] 7.1 `openspec archive add-pixel-grid-overlay` crée `openspec/specs/pixel-grid-overlay/spec.md` et met à jour `openspec/specs/pixel-art-dashboard/spec.md` avec les nouveaux requirements
