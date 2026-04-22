## ADDED Requirements

### Requirement: Le panneau Convertir SHALL exposer un toggle `Inverser masque` qui inverse visuellement l'overlay de détection de fond

Le panneau `.convert-panel` MUST inclure, à côté du bouton `🎯 Détecter fond` et du champ `tolerance`, un toggle `[ ] Inverser masque` (checkbox ou switch). Cette bascule est **purement visuelle côté client** : elle ne modifie AUCUN payload envoyé à `/api/convert` ou `/api/preview`, et en particulier n'altère pas le paramètre `preserve_bg` des étapes du pipeline.

Quand le toggle est `ON`, l'overlay `.bg-mask-overlay` (image retournée par `GET /api/bgmask`) MUST afficher son complément — les pixels du premier-plan (ce qui serait préservé) apparaissent au lieu du fond. L'implémentation utilise `filter: invert(1)` (ou équivalent) appliqué à l'élément `img.bg-mask-overlay`, sans nouvel appel réseau.

Quand le toggle est `OFF`, l'overlay MUST s'afficher en mode normal (fond détecté).

#### Scenario: Toggle OFF par défaut sans état persisté

- **GIVEN** un dashboard fraîchement chargé sans entrée `dashBgInvert` dans `localStorage`
- **WHEN** l'utilisateur clique sur `🎯 Détecter fond` pour afficher l'overlay
- **THEN** le toggle `Inverser masque` SHALL être `OFF` et l'overlay SHALL s'afficher en mode normal (fond visible en opaque)

#### Scenario: Activation du toggle inverse l'overlay sans appel réseau

- **GIVEN** une overlay `.bg-mask-overlay` affichée et le toggle `OFF`
- **WHEN** l'utilisateur active le toggle `Inverser masque`
- **THEN** aucune requête `GET /api/bgmask` SHALL être émise, et `img.bg-mask-overlay` SHALL recevoir le style `filter: invert(1)` (ou équivalent), de sorte que les zones noires et blanches soient inversées instantanément

#### Scenario: L'inversion ne modifie pas les payloads de conversion

- **GIVEN** le toggle `Inverser masque` activé et un pipeline `[{denoise, median}]`
- **WHEN** l'utilisateur clique sur `[▶ Lancer]` ou déclenche un live preview
- **THEN** le payload envoyé à `/api/convert` / `/api/preview` SHALL être strictement identique à celui qui aurait été envoyé avec le toggle désactivé (aucun champ `invert`, `invert_mask` ou équivalent ajouté ; `preserve_bg` inchangé)

### Requirement: L'état du toggle `Inverser masque` SHALL être persisté dans localStorage

L'état du toggle MUST être enregistré dans `localStorage` sous la clé `dashBgInvert` avec les valeurs `"true"` ou `"false"`. Au chargement du dashboard, la valeur persistée SHALL être restaurée. Au prochain affichage de l'overlay, l'état d'inversion SHALL refléter cette valeur restaurée.

#### Scenario: Persistance de l'état après reload

- **GIVEN** le toggle `Inverser masque` activé et l'overlay affichée
- **WHEN** l'utilisateur recharge la page puis re-clique sur `🎯 Détecter fond`
- **THEN** `localStorage.dashBgInvert` SHALL valoir `"true"` après reload, le toggle SHALL apparaître en `ON` dès que l'overlay est affichée, et l'overlay SHALL être inversée immédiatement

#### Scenario: La valeur persistée survit même sans overlay

- **GIVEN** le toggle `Inverser masque` activé, puis l'utilisateur change d'image active (ce qui retire l'overlay)
- **WHEN** l'utilisateur clique sur `🎯 Détecter fond` pour la nouvelle image
- **THEN** la nouvelle overlay SHALL s'afficher directement en mode inversé, car la valeur `dashBgInvert === "true"` a été préservée

### Requirement: Le toggle `Inverser masque` SHALL être désactivé (grisé) sans image active ou sans overlay affichée

Le toggle MUST être `disabled` dans deux cas :
- aucune image n'est sélectionnée comme active (`activeImage === null`) ;
- l'overlay `.bg-mask-overlay` n'est pas présente dans le DOM (détection jamais lancée, ou déjà retirée via re-clic).

Dans l'état `disabled`, le toggle SHALL afficher un style visuel grisé et un tooltip explicatif (ex. « Affiche d'abord le masque via Détecter fond »).

#### Scenario: Toggle désactivé sans image active

- **GIVEN** aucune image active dans la sidebar
- **WHEN** on inspecte le panneau Convertir
- **THEN** le toggle `Inverser masque` SHALL être `disabled` avec un tooltip « Sélectionne une image d'abord » (ou équivalent)

#### Scenario: Toggle désactivé tant qu'aucune détection n'a été lancée

- **GIVEN** une image active et aucune overlay affichée
- **WHEN** on inspecte le panneau Convertir
- **THEN** le toggle `Inverser masque` SHALL être `disabled` avec un tooltip « Affiche d'abord le masque via Détecter fond » (ou équivalent)

#### Scenario: Toggle activé dès que l'overlay est affichée

- **GIVEN** le toggle actuellement `disabled` faute d'overlay
- **WHEN** l'utilisateur clique sur `🎯 Détecter fond` et l'overlay apparaît
- **THEN** le toggle SHALL passer à l'état `enabled` et être interactif immédiatement
