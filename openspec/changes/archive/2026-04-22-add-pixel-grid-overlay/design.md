## Context

Le comparateur central (`main`) superpose déjà deux éléments overlay sur `#cmp-left` :
- `#cmp-overlay` (div) : la moitié de droite qui affiche `cmp-right` via clip.
- `canvas.pixel-axes-overlay` (créé par le toggle `⊹`) : dessine deux flèches d'un pixel natif.

Le pipeline de rendu se base sur :
- `naturalWidth / naturalHeight` de `#cmp-left` pour la taille native.
- `offsetWidth / offsetHeight` rendu pour calculer l'échelle.
- Des listeners `scroll`, `resize`, et le recalcul après chaque zoom (`applyZoom`).

Pour une grille complète, on réutilise exactement ces mêmes signaux — c'est un clone de l'overlay axes mais avec une boucle de dessin sur toute la largeur/hauteur visibles.

## Goals / Non-Goals

**Goals:**
- Afficher une grille 1-pixel ou N-pixels sur toute la surface de `#cmp-left`, alignée sur la grille native.
- Toggle on/off instantané via bouton toolbar et raccourci `G`.
- Pas configurable (1..64) persisté avec le toggle.
- Performance acceptable : redessin < 16 ms même avec 2000×2000 lignes.

**Non-Goals:**
- Remplacer ou fusionner avec le bouton `Axes pixel` existant (fonctionnalité distincte, les deux cohabitent).
- Grille sur `#cmp-right` séparément (un seul canvas suffit, couvre toute la zone comparateur).
- Grilles obliques, isométriques, ou hexagonales.
- Snap-to-grid interactif pour placer des outils (pas utile ici).

## Decisions

**Décision 1 — Canvas indépendant `#grid-overlay`.**
Plutôt que de réutiliser le canvas des axes (ce qui forcerait une dépendance entre les deux toggles), on ajoute un canvas séparé, z-index juste au-dessus de `#cmp-left` et en dessous de `#cmp-overlay` pour que le comparateur slider reste interactif.

Stack z-index :
- `#cmp-left` (img)  → z-index auto
- `#grid-overlay` (canvas) → z-index 10
- `#cmp-overlay` (div slider) → z-index 20
- `canvas.pixel-axes-overlay` → z-index 30 (au-dessus de tout)
- `#cmp-handle` → z-index 40
- `.cmp-toolbar` → z-index 50

**Décision 2 — Algorithme de dessin.**
À chaque redessin :
1. Lire `scale = cmp-left.offsetWidth / cmp-left.naturalWidth`.
2. `pixelScreen = scale * step` (taille en pixels écran d'une case de grille).
3. Si `pixelScreen < 2`, ne pas dessiner (illisible, éviter le blur). Afficher un tooltip warning discret.
4. Sinon, boucler `for (x = 0; x < width; x += pixelScreen) drawLine(x, 0, x, height)` et idem vertical.
5. Traits : `strokeStyle = rgba(255, 255, 255, 0.15)`, `lineWidth = 1`. Lignes majeures (multiples de 8) : `rgba(255, 255, 255, 0.3)`, `lineWidth = 1.5`.

**Décision 3 — Raccourci clavier `G`.**
Cohérent avec `H` pour historique. Handler attaché sur `document.keydown`, ignoré quand le focus est sur un champ `input/textarea/select` pour ne pas interférer avec la saisie.

**Décision 4 — Input `pas` (step) dans la toolbar.**
Petit `<input type="number" min="1" max="64" value="1">` à droite du bouton `🔳 Grille`, visible uniquement quand le toggle est actif (évite d'encombrer la toolbar). Le changement du pas déclenche un redessin sans toucher au toggle.

**Décision 5 — Persistance.**
- `localStorage.dashGridOn` : `"true"` / `"false"`.
- `localStorage.dashGridStep` : `"1"` .. `"64"`.
- Restaurés au chargement. Si `dashGridOn === "true"` au boot, la grille apparaît après le premier rendu de `#cmp-left`.

**Décision 6 — Distinction visuelle vs axes.**
- Axes pixel : vert `#00ff88`, deux flèches courtes.
- Grille : blanc translucide (15-30% opacité), lignes fines continues.
Les deux couleurs et styles ne risquent pas d'être confondus si l'utilisateur active les deux ensemble.

## Risks / Trade-offs

- **Risque** : trop de lignes à dessiner quand `step=1` et image zoomée à ×16 sur un 2048×2048 → 32k lignes, possible jank.
  **Mitigation** : boucle simple `beginPath` + `moveTo/lineTo` + un seul `stroke()` final est très rapide (< 5 ms même pour 10k segments). Si nécessaire, batcher par tranches ou utiliser un Path2D.

- **Risque** : grille visible à travers les parties sombres de l'image seulement, invisibles sur fond clair.
  **Mitigation** : `mix-blend-mode: difference` sur le canvas → lignes toujours contrastées. À tester ; fallback sur blanc+ombre si l'option pose problème sur certains sprites.

- **Risque** : activation simultanée de `Axes pixel` + `Grille` → encombrement visuel.
  **Mitigation** : cohabitation autorisée mais non recommandée ; pas de logique d'exclusion mutuelle (laisser l'utilisateur choisir).

- **Trade-off** : pas de mise à l'échelle côté GPU (WebGL) → suffisant pour la taille des sprites traités (< 4k), pas d'over-engineering.

## Open Questions

- Le raccourci `G` entre-t-il en conflit avec un autre binding ? Vérifier dans le code actuel du dashboard (au moment de l'implémentation).
- Voulons-nous une couleur configurable ? Pour l'itération 1, fixer à blanc translucide ; ajouter plus tard si besoin.
