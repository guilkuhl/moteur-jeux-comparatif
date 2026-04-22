## Why

Quand l'utilisateur clique sur `🎯 Détecter fond`, l'overlay `.bg-mask-overlay` affiche actuellement **le fond** (pixels considérés comme arrière-plan). Pour juger visuellement la qualité de la détection sur des sprites au premier-plan complexe (personnage, objet), il est souvent plus parlant de voir **ce qui reste** (le premier-plan conservé) plutôt que ce qui sera masqué. Fournir une bascule « Inverser masque » permet de comparer les deux vues sans relancer la détection et sans changer le comportement de `/api/convert` ou `/api/preview`.

## What Changes

- Ajouter un toggle `[ ] Inverser masque` dans `.convert-panel`, à côté du bouton `🎯 Détecter fond` et du champ `tolerance`.
- Quand le toggle est `ON`, l'overlay `.bg-mask-overlay` SHALL afficher le premier-plan (complément du masque actuel) au lieu du fond.
- Le toggle SHALL être persisté dans `localStorage` sous la clé `dashBgInvert`.
- Le toggle SHALL être désactivé (grisé) quand aucune image active, ou quand l'overlay n'est pas affichée.
- **Pur affichage client** : aucune modification des payloads envoyés à `/api/convert` ou `/api/preview`. Le paramètre `preserve_bg` des étapes reste indépendant de cette bascule.

## Capabilities

### New Capabilities
<!-- Aucune nouvelle capability : feature incrémentale sur le dashboard existant -->

### Modified Capabilities
- `pixel-art-dashboard`: ajout d'une exigence sur le toggle « Inverser masque » et son effet visuel ; clarification que la bascule n'impacte pas les payloads backend.

## Impact

- **Frontend (pixel-lab/dashboard/index.html)** : ajout d'un `<input type="checkbox" id="bg-invert-toggle">` dans le bloc bg-detect, logique `toggleBgInvert()`, lecture/écriture `localStorage.dashBgInvert`, application du style d'inversion sur `.bg-mask-overlay`.
- **Backend (pixel-lab/server/app.py)** : aucun changement obligatoire (option B du design conservée comme variante).
- **Specs (openspec/specs/pixel-art-dashboard/spec.md)** : ajout d'un requirement « Le panneau Convertir SHALL exposer un toggle Inverser masque … ».
- **Tests visuels** : un scénario à ajouter pour vérifier l'état désactivé + l'effet visuel attendu.
