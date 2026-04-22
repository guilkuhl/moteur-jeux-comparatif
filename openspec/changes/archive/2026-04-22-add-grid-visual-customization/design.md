## Context

`drawPixelGrid()` actuelle hardcode `rgba(255,255,255,0.15)` pour les lignes normales et `rgba(255,255,255,0.3)` pour les lignes majeures. Le canvas utilise `mix-blend-mode: difference` via CSS pour rester contrasté.

## Goals / Non-Goals

**Goals:**
- 3 contrôles visibles uniquement quand la grille est active.
- Persistance localStorage.
- Redessin instantané au changement.

**Non-Goals:**
- Couleurs séparées pour lignes normales vs majeures (compliquerait l'UI sans bénéfice clair pour v1).
- Sauvegarde des préférences par image (config globale au dashboard).
- Plus de 3 modes de blend (suffit pour 99% des cas).

## Decisions

**Décision 1 — Une seule couleur, opacité fait varier les lignes normales/majeures.**
Lignes normales = `rgba(R, G, B, opacity)`.
Lignes majeures = `rgba(R, G, B, opacity * 2)` (clamp 1.0).

Garde la cohérence visuelle (lignes majeures = double densité visuelle).

**Décision 2 — `mix-blend-mode` appliqué via CSS sur le canvas.**
Au lieu de calculer le blend pixel-par-pixel en JS, on applique simplement `canvas.style.mixBlendMode = blend` côté CSS. Performance optimale.

**Décision 3 — Compact UI.**
Les 3 contrôles tiennent dans la toolbar à côté de `#grid-step-label` :
- color picker (24×20 px)
- range slider (60 px)
- select blend (60 px)

Total ~150 px, acceptable.

## Risks / Trade-offs

- **Risque** : opacité × 2 pour les lignes majeures peut dépasser 1.0 → clamp.
  **Mitigation** : `Math.min(1, opacity * 2)`.

- **Trade-off** : pas de personnalisation séparée majeur/normal → simple mais limité. Si demande ultérieure, ouvrir un follow-up.
