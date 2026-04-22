## 1. Structure HTML et CSS Grid du layout principal

- [x] 1.1 Créer un wrapper `<div class="app-shell">` en haut de `<body>` englobant les 3 colonnes
- [x] 1.2 Définir les variables CSS `:root { --left-w: 280px; --right-w: 0px; }` et `body { margin:0; height:100vh; overflow:hidden }`
- [x] 1.3 Définir `.app-shell { display:grid; grid-template-columns: var(--left-w) 1fr var(--right-w); height:100vh; transition: grid-template-columns 0.22s ease; }`
- [x] 1.4 Créer 3 éléments enfants : `<aside id="left-col">`, `<main id="center-col">`, `<aside id="right-col">`
- [x] 1.5 Retirer l'ancien `<header>` et répartir son contenu (badge, statut API) dans `#left-col`
- [x] 1.6 Tester visuellement : les 3 colonnes apparaissent, la centrale prend tout l'espace restant, aucun scroll global

## 2. Sidebar gauche : migration et densification

- [x] 2.1 Structurer `#left-col` en 3 zones verticales : header compact (50px), liste images (`flex:1 1 auto; overflow-y:auto`), panneau Convertir (`flex:0 0 auto; max-height:60vh; overflow-y:auto`)
- [x] 2.2 Appliquer `#left-col { display:flex; flex-direction:column; height:100vh; overflow:hidden; }`
- [x] 2.3 Déplacer le HTML actuel de la sidebar images dans la zone images de `#left-col`
- [x] 2.4 Déplacer le HTML actuel du panneau Convertir (`.convert-panel`) dans la zone panneau de `#left-col`
- [x] 2.5 Compacter le CSS des `.step-row` pour tenir dans 280 px : passer en `flex-direction: column` ou utiliser `grid-template-columns: 1fr auto` pour séparer les 2 selects et les boutons d'action
- [x] 2.6 Vérifier que la liste d'images scroll indépendamment sans affecter le panneau Convertir
- [x] 2.7 Vérifier que le panneau Convertir scroll interne si contenu long (nombreuses étapes)

## 3. Colonne centrale : comparateur plein écran

- [x] 3.1 Structurer `#center-col` comme conteneur unique du comparateur : `position: relative; height: 100vh; width: 100%; overflow: hidden;`
- [x] 3.2 Déplacer le HTML du `.compare-card` / slider existant dans `#center-col`
- [x] 3.3 Retirer les `max-width/max-height` actuels du `.compare-card` : il doit remplir 100% de son conteneur
- [x] 3.4 Ajuster `.compare-body { height: 100% }` pour que la zone image prenne toute la hauteur disponible
- [x] 3.5 Vérifier que le divider et la poignée continuent à fonctionner (drag, zoom, pan)
- [x] 3.6 Retirer l'ancienne grille d'iters et la barre tri/filtre de cette zone (déplacées en §5)

## 4. Toolbar overlay en haut du comparateur

- [x] 4.1 Créer dans `#center-col` un `<div class="cmp-toolbar">` en `position: absolute; top:0; left:0; right:0; height:40px; z-index:200; background:rgba(10,10,20,0.55); backdrop-filter:blur(8px)`
- [x] 4.2 Déplacer dans la toolbar : nom du sprite actif (gauche), labels G/D (centre), boutons zoom −/+/reset/axes/toggle (droite)
- [x] 4.3 Ajouter un span pour le label de timing preview « Calculé en Xms · cache=N » dans la toolbar (caché si pas en mode live)
- [x] 4.4 Retirer l'ancien `.compare-footer` et l'ancien `.compare-header` (leur contenu essentiel est désormais dans la toolbar)
- [x] 4.5 Vérifier que les clics sur la toolbar ne propagent pas vers le comparateur (pan drag accidentel sur le fond de toolbar)

## 5. Panneau Historique à droite

- [x] 5.1 Structurer `#right-col` : `height:100vh; overflow-y:auto; background:var(--surface); border-left:1px solid var(--border); width: var(--right-w); transition: width 0.22s`
- [x] 5.2 Créer l'en-tête du panneau : titre « Historique des iters » + bouton `×` de fermeture
- [x] 5.3 Déplacer la barre tri/filtre actuelle dans `#right-col`
- [x] 5.4 Déplacer la grille d'iters (`<div id="iter-grid">`) dans `#right-col`, en ajustant sa grille CSS pour tenir dans 320 px
- [x] 5.5 Vérifier que le clic sur un iter fonctionne toujours (modifie `compareRight`, refresh du comparateur central)
- [x] 5.6 Vérifier que le sort/filter reste fonctionnel dans le nouveau contexte

## 6. Rétractation des panneaux + persistance

- [x] 6.1 Ajouter un bouton `<button class="collapse-btn collapse-left">‹</button>` en bord droit de `#left-col`
- [x] 6.2 Ajouter un bouton `<button class="collapse-btn collapse-right">›</button>` en bord gauche de `#right-col`
- [x] 6.3 Implémenter `toggleLeftPanel()` qui alterne `--left-w` entre `280px` et `0px` via `document.documentElement.style.setProperty`, persiste dans `localStorage.dashLeftOpen`
- [x] 6.4 Implémenter `toggleRightPanel()` pareil, avec `320px` et `0px`, persiste `dashRightOpen`
- [x] 6.5 Au chargement, lire `localStorage.dashLeftOpen` et `dashRightOpen` et appliquer les valeurs initiales (via IIFE au plus tôt pour éviter le flash)
- [x] 6.6 Ajouter un bouton `📜 Historique` dans la sidebar gauche (pied de la liste images) qui appelle `toggleRightPanel()`
- [x] 6.7 Ajouter un listener `document.addEventListener('keydown', ...)` pour toggle via `H`
- [x] 6.8 Tester : la rétractation est fluide (220 ms), l'état persiste après reload

## 7. Poignée slider : viewport-centric dans le nouveau layout

- [x] 7.1 Vérifier que `updateHandleVerticalPos()` (implémenté précédemment) fonctionne dans le nouveau layout — dans 99% des cas le comparateur = 100vh donc `getBoundingClientRect().top ≈ 0` et la poignée est au centre de l'écran
- [x] 7.2 Mettre à jour la logique pour tenir compte de la toolbar de 40 px en haut : `visibleTop = max(40, -rect.top)` (pour que la poignée ne passe pas sous la toolbar)
- [x] 7.3 Tester en redimensionnant la fenêtre et en ouvrant/fermant les panneaux — la poignée doit toujours être visible et bien centrée

## 8. Styling et polissage

- [x] 8.1 Ajuster les paddings/margins de la sidebar pour une densité visuelle cohérente avec Upscayl (items de liste ~40 px de haut, spacing vertical entre zones 12 px)
- [x] 8.2 Ajouter une ombre discrète entre les colonnes : `#left-col { box-shadow: 2px 0 8px rgba(0,0,0,.2); }` et symétrique pour `#right-col`
- [x] 8.3 Tester le mode sombre et clair (thème existant) — les transparences de la toolbar overlay doivent rester lisibles dans les deux modes
- [x] 8.4 Vérifier que tous les tooltips existants (sur algos, méthodes, paramètres) fonctionnent toujours dans la sidebar rétrécie

## 9. Nettoyage du code legacy

- [x] 9.1 Retirer l'ancien CSS du layout (anciennes règles de largeur fixe, `max-width` sur la sidebar, etc.)
- [x] 9.2 Retirer les éléments HTML orphelins (ancien header global, ancien footer, ancienne zone de détails d'iter si présente)
- [x] 9.3 Retirer les media queries responsive devenues obsolètes (V1 desktop-first)
- [x] 9.4 Vérifier qu'aucune référence à l'ancien `renderContent()` / ancien layout ne reste — la grille d'iters rendue dans `#right-col` uniquement

## 10. Validation manuelle end-to-end

- [x] 10.1 Démarrer le serveur, ouvrir le dashboard : le layout 2 colonnes apparaît, image-comparateur centrale plein écran
- [x] 10.2 Sélectionner une image : le comparateur affiche la source, la poignée est centrée verticalement
- [x] 10.3 Activer live preview, ajouter une étape, tweaker un slider : le preview apparaît à droite du comparateur, zéro scroll nécessaire
- [x] 10.4 Cliquer le bouton `📜 Historique` : le panneau droit s'ouvre avec la grille d'iters. Cliquer un iter : le comparateur bascule pour afficher cet iter
- [x] 10.5 Fermer la sidebar gauche (`<`) : le comparateur s'étend davantage, la poignée reste centrée
- [x] 10.6 Fermer les deux panneaux : le comparateur occupe 100% de l'écran, poignée au centre pixel-parfait
- [x] 10.7 Recharger la page : les états des panneaux (ouvert/fermé) sont restaurés depuis localStorage
- [x] 10.8 Tester que le bouton `[▶ Lancer]` fonctionne toujours et produit un iter dans le panneau Historique
- [x] 10.9 Tester que la détection de fond (si add-background-detection est appliqué) fonctionne dans le nouveau layout : bouton + overlay + toggle restent accessibles dans la sidebar
