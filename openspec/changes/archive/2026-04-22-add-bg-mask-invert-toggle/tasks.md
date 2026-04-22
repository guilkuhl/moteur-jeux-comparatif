## 1. UI — Toggle dans le panneau Convertir

- [ ] 1.1 Ajouter un `<input type="checkbox" id="bg-invert-toggle">` accompagné de son `<label>` « Inverser masque » dans le bloc bg-detect de `pixel-lab/dashboard/index.html`, juste en dessous du toggle `Préserver fond`
- [ ] 1.2 Ajouter un attribut `title` / tooltip contextuel (« Affiche d'abord le masque via Détecter fond » quand disabled) et le style `disabled` par défaut (greyed out + curseur)
- [ ] 1.3 Vérifier que la disposition reste lisible dans la sidebar 280 px (empiler si nécessaire)

## 2. Logique — Activation / désactivation

- [ ] 2.1 Implémenter une fonction `refreshBgInvertToggle()` qui recalcule l'état `disabled` selon `activeImage === null` OU absence de `img.bg-mask-overlay` dans le DOM
- [ ] 2.2 Appeler `refreshBgInvertToggle()` dans : `selectImage()`, `toggleBgOverlay()` (après ajout/retrait de l'overlay), et au chargement initial
- [ ] 2.3 Brancher le `onchange` du toggle sur une fonction `setBgInvert(checked)` qui applique/retire `filter: invert(1)` sur `img.bg-mask-overlay` et écrit `localStorage.dashBgInvert`

## 3. Persistance `localStorage`

- [ ] 3.1 Au chargement du dashboard, lire `localStorage.dashBgInvert` (via try/catch pour gérer le mode privé) et restaurer l'état `checked` du toggle
- [ ] 3.2 À chaque affichage d'overlay (`toggleBgOverlay` vient de l'afficher), appliquer immédiatement le style d'inversion si `dashBgInvert === "true"`
- [ ] 3.3 À chaque changement du toggle, sérialiser `"true"` / `"false"` dans `localStorage.dashBgInvert`

## 4. Style CSS

- [ ] 4.1 Ajouter une règle CSS `.bg-mask-overlay.inverted { filter: invert(1); }` (ou approche équivalente) dans la feuille de style embarquée
- [ ] 4.2 Vérifier qu'`image-rendering: pixelated` reste bien hérité sur l'overlay inversée

## 5. Tests visuels

- [ ] 5.1 Scénario : toggle OFF par défaut → overlay non inversée (fond visible)
- [ ] 5.2 Scénario : clic sur toggle → overlay inversée sans appel réseau additionnel (vérifier via devtools Network)
- [ ] 5.3 Scénario : payload `/api/preview` et `/api/convert` strictement identiques avec toggle ON ou OFF
- [ ] 5.4 Scénario : reload de la page préserve l'état du toggle et l'applique à la prochaine overlay
- [ ] 5.5 Scénario : toggle disabled quand aucune image active, et disabled quand overlay non affichée

## 6. Mise à jour de la capability

- [ ] 6.1 Après archivage du change, vérifier que `openspec/specs/pixel-art-dashboard/spec.md` a bien reçu les 3 nouveaux requirements via `openspec archive`
