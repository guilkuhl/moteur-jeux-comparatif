## Context

Le dashboard actuel utilise un layout en flow vertical : header, sidebar gauche (images), contenu principal avec empilement de (comparateur + barre filtres + grille iters + panneau convertir). Sur un écran 1920×1080, le comparateur occupe ~40% de la hauteur visible, le reste étant mangé par la grille d'iters et le panneau convertir en dessous. Pour le tuning en mode live, l'utilisateur veut voir le résultat le plus grand possible tout en ajustant les paramètres.

La référence visuelle fournie (Upscayl 2.11.5) propose un pattern éprouvé : sidebar fixe à gauche, image plein écran à droite, poignées de rétractation des panneaux. Ce pattern correspond mieux à un usage « réglage image unique, je veux tout voir ».

Contraintes :
- Ne casser aucune fonctionnalité existante (live preview, grille iters, sort/filter, détails iter, bouton Lancer, mode sombre/clair).
- Rester en HTML/CSS/JS vanilla dans `index.html` (cohérent avec la base existante).
- Le comparateur slider existe déjà, on ne le refait pas — on le repositionne et on lui donne toute la place.

## Goals / Non-Goals

**Goals :**
- Comparateur occupant 100% de la hauteur de la colonne droite et toute sa largeur.
- Sidebar gauche rétractable (bouton `<`) pour passer en vrai plein écran image.
- Panneau Convertir intégré dans la sidebar gauche (pas une zone séparée en bas).
- Grille d'iters + tri/filtre accessibles via un panneau rétractable (`>`) ouvrable à la demande.
- Poignée du slider positionnée au centre du **viewport visible**, pas du body image (correction du bug actuel où elle sort de l'écran sur grandes images).
- Zéro scroll sur la page principale en usage nominal (le scroll reste autorisé à l'intérieur de panneaux si nécessaire).

**Non-Goals :**
- Refaire la logique du comparateur, du zoom, du drag, du live preview — tout reste.
- Refaire l'API ou les algos.
- Supporter le responsive mobile (le dashboard reste desktop-first).
- Ajouter un dark/light toggle avancé (on garde ce qui existe).
- Déplacer le détail textuel d'un iter vers un tooltip (V2 si besoin).

## Decisions

### D1 — Structure 2 colonnes CSS Grid vs Flexbox

On utilise **CSS Grid** sur le `body` (ou un wrapper `.app-shell`) : `grid-template-columns: var(--left-w, 280px) 1fr var(--right-w, 0px); grid-template-rows: 100vh`. Les variables `--left-w` et `--right-w` permettent la rétractation (0px = panneau fermé, 280px ou 320px = ouvert) avec transition CSS.

**Pourquoi Grid** : le layout est strictement 2 colonnes + éventuellement panneau droit, hauteur fixe. Flexbox marcherait aussi mais Grid rend la gestion des largeurs via CSS variables plus propre (une seule ligne pour rétracter).

**Alternative rejetée** : panneaux flottants en `position: fixed`. Trop de JS à écrire pour gérer les overlaps et les tailles.

### D2 — Sidebar gauche : contenu et scroll interne

Contenu empilé verticalement dans cet ordre :
1. Header minimal (logo + titre + badge version) — ~50 px
2. Liste des images source (scrollable à l'intérieur de la sidebar) — flex: 1 1 auto, min-height: 100px
3. Panneau Convertir (builder pipeline + toggles live/fullres/preserve_bg + bouton Lancer + status) — flex: 0 0 auto, max-height: 60vh, scroll interne si besoin
4. Pied : bouton `Historique` pour ouvrir le panneau droit + bouton rétraction `<`

La sidebar entière a `overflow: hidden`, chaque zone scrolle individuellement si son contenu dépasse.

**Pourquoi** : garder les contrôles visibles et stables pendant qu'on tweak. La liste d'images prend l'espace dispo, le builder est dense mais visible.

### D3 — Panneau droit « Historique » : rétractable, largeur fixe

Largeur fixe 320 px quand ouvert, 0 quand fermé. Contient la grille actuelle d'iters + le tri/filtre. Un chevron `>` en bord droit de l'écran permet d'ouvrir/fermer. Raccourci clavier `H` pour toggle.

**Pourquoi** : on préserve la possibilité de voir tous les iters, mais ce n'est plus la vue par défaut. L'utilisateur ouvre le panneau quand il veut comparer ou sélectionner un iter spécifique.

### D4 — Comparateur : tout l'espace restant

La zone centrale (`grid-column: 2`) est un seul `.compare-card` qui prend `height: 100vh; width: 100%;`. L'image source affichée en left half, preview/iter choisi en right half, divider glissant.

**Pourquoi** : c'est l'élément principal du dashboard, il mérite toute la place. Le comparateur existant fonctionne déjà — il suffit de le laisser grandir (enlever les `max-width/max-height` actuels).

### D5 — Poignée slider : viewport-centric

Le fix actuel calcule le centre de la portion visible via `getBoundingClientRect`. Avec le nouveau layout, le comparateur remplit 100% de la hauteur donc la logique « position = centre du viewport visible du body » revient à « centre vertical de l'écran ». Le scroll listener existant devient quasi no-op dans le nouveau layout mais reste utile si l'utilisateur scrolle la page pour d'autres raisons (ex. si la sidebar overflow).

**Pourquoi** : réutiliser le code déjà en place, zéro complexité supplémentaire. Dans le nouveau layout le viewport = la zone comparateur pour 99% des cas.

### D6 — Rétractation des panneaux : CSS variables + transition

Deux variables CSS `--left-w` et `--right-w` définies sur `:root`. Un simple bouton toggle modifie leur valeur (via `document.documentElement.style.setProperty`). Transition : `transition: grid-template-columns 0.22s ease`.

**Pourquoi** : animation fluide, pas de JavaScript de mesure, pas de `requestAnimationFrame`. L'état collapsed/expanded est stocké dans `localStorage` pour persister entre sessions.

### D7 — Toolbar comparateur : minimale, overlaid sur l'image

En haut du comparateur, une barre semi-transparente (`background: rgba(0,0,0,0.4); backdrop-filter: blur(8px)`) avec : nom de l'image active, label Gauche/Droite, boutons zoom, toggle axes pixel, label de timing preview. Hauteur ~40 px.

**Pourquoi** : maximum de pixels dédiés à l'image, tout en gardant les contrôles accessibles.

### D8 — Header global supprimé

Le header actuel (badge « ⚡ Pixel Lab », info serveur) est retiré — son contenu passe en haut de la sidebar gauche. Libère 50 px verticaux pour l'image.

**Pourquoi** : sur 1080 px de hauteur, 50 px = ~5% d'espace gagné pour l'image, non négligeable.

## Risks / Trade-offs

- **[Risque] Perte d'accès rapide à la grille d'iters** → utilisateurs habitués voient la grille par défaut, maintenant ils doivent ouvrir un panneau. Mitigation : raccourci `H`, bouton visible en bas de la sidebar, ouverture automatique la 1ère fois (onboarding).

- **[Risque] Sidebar gauche trop dense** → le panneau Convertir a beaucoup de contrôles (builder + toggles + bouton + live row + bg row). À 280 px de large, ça peut être serré. Mitigation : scroll interne autorisé, les étapes du builder passent en `flex-direction: column` compact, le tooltip-ing des paramètres (déjà implémenté) évite d'ajouter du texte visible.

- **[Risque] Comparateur plein écran avec petite image (64×64 sprite)** → l'image s'étire (en nearest-neighbor pour rester pixelated) et occupe tout l'espace. Acceptable mais peut être lourd visuellement. Mitigation : garder le zoom à 1× par défaut avec lettreboxing propre (background noir autour), et le zoom/pan déjà existant permet de dézoomer si besoin.

- **[Trade-off] Pas de responsive mobile** → accepté, Pixel Lab est un outil desktop. Si besoin futur : media queries `@media (max-width: 768px)` pour basculer en layout simple colonne.

- **[Trade-off] Le nouveau layout casse la hauteur d'écran supposée** → si l'utilisateur a une fenêtre très petite (≤ 500 px de haut), la sidebar va scroller beaucoup. Mitigation : `min-height: 500px` sur le `.app-shell` avec un warning discret si trop petit.

## Migration Plan

Aucune migration de données. Pure refonte UI :
1. Développer le nouveau layout en parallèle (feature flag `?v=2` sur l'URL pour l'activer pendant le dev).
2. Tester avec les workflows existants : sélection image, live preview, Lancer, Détecter fond, Historique.
3. Basculer par défaut quand validé, laisser `?v=1` pour rollback pendant une semaine.
4. Retirer l'ancien layout après validation.

## Open Questions

- Faut-il garder le mode « sidebar fermée + panneau historique fermé » comme préférence persistée, ou toujours démarrer sidebar ouverte ? (penchant pour « last state wins » via localStorage)
- Le bouton Historique doit-il afficher un compteur d'iters (badge) ? (utile mais demande de la logique supplémentaire)
- Faut-il un raccourci clavier global pour toggle live preview ? Actuellement il faut cliquer le toggle dans la sidebar. (V2)
