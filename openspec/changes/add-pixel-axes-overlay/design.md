## Context

Le comparateur du dashboard (`dashboard/index.html`) affiche les images via un `<img>` dans une `.compare-body` zoomable. À chaque zoom, l'image est agrandie via CSS `transform: scale(Z) translate(Px, Py)`. La taille d'un pixel natif à l'écran vaut donc `Z × (largeur_affichée / largeur_naturelle)`. L'overlay doit rester aligné avec l'image réelle, recalculé à chaque changement de zoom.

## Goals / Non-Goals

**Goals:**
- Dessiner deux axes fléchés verts (→ et ↓) dont la longueur = 1 pixel natif à l'échelle courante.
- Repositionner et redessiner l'overlay à chaque changement de zoom/pan.
- Toggle on/off via un bouton dans le footer du comparateur.
- S'appliquer aussi sur les cartes individuelles (même toggle global).

**Non-Goals:**
- Pas de règle graduée complète (juste les deux vecteurs unitaires).
- Pas de configuration de couleur ou d'épaisseur (vert fixe, 2px).
- Pas de support touch pour déplacer l'origine des axes.
- Pas d'export de l'image avec les axes incrustés.

## Decisions

### D1. Canvas superposé à l'image plutôt que SVG ou DOM

**Choix :** `<canvas>` en `position: absolute` au-dessus du zoom layer.

**Pourquoi :** Le canvas est repositionné et redessiné programmatiquement à chaque frame ; pas de reflow DOM. Le SVG nécessiterait de gérer des transformations inverses plus complexes. Le canvas offre un API de dessin direct (flèches, lignes) sans dépendance.

**Alternatives :** SVG inline (rejeté pour verbosité), div DOM (rejeté pour manque de précision sub-pixel).

### D2. Calcul de la taille d'un pixel natif

La taille d'affichage d'un pixel natif = `cmpZ × (body_width / img_natural_width)`. Cette valeur est recalculée à chaque `applyCmpZoom()`. L'origine des axes est fixée au coin supérieur gauche de l'image dans le repère du canvas (tenant compte du pan `cmpPx, cmpPy`).

### D3. Toggle global unique

Un seul booléen `showPixelAxes` contrôle l'affichage sur le comparateur. Le canvas est caché/montré sans le recréer. L'état est persisté dans une variable JS locale (pas de localStorage pour cette V1).

## Risks / Trade-offs

- **[Désynchronisation axes/zoom]** → Mitigation : `drawPixelAxes()` est appelé depuis `applyCmpZoom()` à chaque changement. Pas de désync possible.
- **[Image pas encore chargée]** → L'image naturelle peut avoir `naturalWidth === 0` avant le load. → Mitigation : écouter l'événement `load` sur `cmp-left` avant de dessiner.
- **[Pixel natif trop petit à zoom×1]** → À zoom×1 sur une grande image, 1 pixel peut être < 1px écran. Afficher un minimum de 4px pour rester visible.
