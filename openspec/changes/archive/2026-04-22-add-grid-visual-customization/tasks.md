## 1. Ajout des contrôles dans la toolbar

- [ ] 1.1 Ajouter `<input type="color" id="grid-color">`, `<input type="range" id="grid-opacity">`, `<select id="grid-blend">` dans `.cmp-toolbar` après `#grid-step-label`
- [ ] 1.2 CSS pour masquer les 3 contrôles quand grille OFF (réutilise `.visible` class du grid-step)

## 2. Persistance localStorage

- [ ] 2.1 Au load, lire `dashGridColor` (défaut `#ffffff`), `dashGridOpacity` (défaut `0.15`), `dashGridBlend` (défaut `difference`) et appliquer aux contrôles
- [ ] 2.2 À chaque `oninput`/`onchange`, écrire la nouvelle valeur dans `localStorage` puis appeler `drawPixelGrid()`

## 3. Refactor drawPixelGrid

- [ ] 3.1 Lire les 3 valeurs depuis les contrôles (ou variables internes)
- [ ] 3.2 Convertir hex `#RRGGBB` en `rgba(R, G, B, opacity)` pour lignes normales
- [ ] 3.3 Pour lignes majeures, opacité = `min(1, opacity * 2)`
- [ ] 3.4 Appliquer `canvas.style.mixBlendMode = blend`

## 4. refreshGridBtn

- [ ] 4.1 Étendre `refreshGridBtn()` pour aussi montrer/masquer les 3 nouveaux contrôles selon `gridOn`

## 5. Tests

- [ ] 5.1 Couleur rouge → lignes rouges visibles
- [ ] 5.2 Opacité 1.0 → lignes pleinement opaques (lignes majeures clamped à 1.0)
- [ ] 5.3 Blend `normal` → canvas affiché en couleur source pure
- [ ] 5.4 Reload page : couleur/opacité/blend restaurés depuis localStorage
- [ ] 5.5 Toggle grille OFF → 3 contrôles masqués
