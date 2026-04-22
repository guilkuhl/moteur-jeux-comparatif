## Context

`drawPixelGrid()` actuelle (implémentée dans `add-pixel-grid-overlay`) :

```js
const scale = w / img.naturalWidth;
const pixelScreen = scale * gridStep;
if (pixelScreen < 2) { canvas.hide(); warning.show(); return; }
// dessine à pixelScreen
```

La demande : remplacer la branche « hide » par une boucle qui cherche le plus petit multiplicateur de 2 permettant d'atteindre le seuil.

## Goals / Non-Goals

**Goals:**
- L'utilisateur voit toujours une grille alignée sur les pixels natifs, même à zoom modéré.
- L'affichage mentionne l'auto-adapt quand il intervient (traçabilité pour l'utilisateur).
- La valeur saisie dans `#grid-step` n'est jamais mutée par l'auto-adapt (pas de surprise).

**Non-Goals:**
- Auto-adapt « descendant » (si zoom très élevé, on ne subdivise pas en fractions de pixel) — la granularité minimale reste 1 pixel natif.
- Détection adaptative basée sur la couleur de l'image ou le contraste.
- Configurer la séquence d'auto-adapt (on fige 1→2→4→8→16→32→64).

## Decisions

**Décision 1 — Séquence d'auto-adapt : puissances de 2.**
Partant du `stepUser`, on cherche le plus petit `stepEff = stepUser × 2ⁿ` tel que `scale × stepEff ≥ 2`. La raison : les puissances de 2 sont stables visuellement (doubler la granularité), et 64 reste lisible même sur de très petites vignettes. Alternatives rejetées :
- Séquence arithmétique `stepUser, stepUser+1, …` : produirait des grilles visuellement désalignées au zoom (effet de moiré).
- Multiples de 4, 8 seulement : saut trop brutal (step=1 → step=8 directement) alors qu'on pourrait avoir step=2 acceptable.

**Décision 2 — Clamper stepEff à 64.**
Au-delà, la grille devient trop clairsemée pour être utile. Si stepEff > 64 est nécessaire, on masque et affiche le warning existant.

**Décision 3 — Affichage de l'auto-adapt en toolbar.**
Deux variantes considérées :
- **(a) Label texte à côté du bouton** : `🔳 · step 1→8` en `<span id="grid-step-label">`. Clair, visible, coûteux en espace.
- **(b) Titre du bouton uniquement** : `title="Grille — step user 1, effectif 8"`. Moins visible mais compact.

**Choix : (a)** pour transparence. Quand `stepEff === stepUser`, on n'affiche que `step 8` (sans flèche).

**Décision 4 — Input step reste = stepUser.**
Si l'utilisateur saisit 1 et que l'auto-adapt bumpe à 8, la valeur dans `#grid-step.value` reste « 1 » et `localStorage.dashGridStep` aussi. Sinon un zoom in/out ferait osciller la valeur utilisateur sans qu'il comprenne.

**Décision 5 — Les lignes majeures restent tous les 8 stepEff.**
Pas de changement : le highlight « tous les 8 » est relatif au step effectif. Quand stepEff=8, chaque ligne est déjà une ligne majeure (coïncidence — OK, c'est juste toutes pleines-fortes).

## Risks / Trade-offs

- **Risque** : confusion utilisateur quand stepUser ≠ stepEff.
  **Mitigation** : label explicite `step 1→8` + tooltip « Grille auto-adaptée : zoome pour descendre au step demandé ».

- **Risque** : le bump à step=8 peut donner l'illusion qu'on masque des pixels intermédiaires.
  **Mitigation** : c'est l'inverse — le bump évite le flou de sub-pixel. Les pixels natifs sont toujours visibles dans l'image elle-même.

- **Trade-off** : calcul en `log2` à chaque redessin. Coût négligeable (< 1 μs).

## Open Questions

- Faut-il ajuster aussi le comportement quand l'overlay `axes pixel` est actif pour éviter qu'ils se gênent mutuellement ? → Hors scope de ce change ; les deux peuvent cohabiter comme aujourd'hui.
