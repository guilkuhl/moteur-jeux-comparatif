## Context

Le panneau Convertir expose déjà :
- Bouton `🎯 Détecter fond` (`#btn-detect-bg`) qui déclenche `GET /api/bgmask?image=<basename>&tolerance=<n>` puis affiche un `img.bg-mask-overlay` (position absolute, z-index 50) superposé sur `#cmp-left` dans le comparateur central.
- Champ `#bg-tolerance` (0-50, défaut 8).
- Toggle `#preserve-bg-toggle` (ajoute `preserve_bg: true` aux params envoyés à `/api/preview` et `/api/convert`).

Le masque PNG retourné par le serveur est un masque binaire 1 canal (blanc = fond détecté, noir = premier-plan) ou RGBA selon l'implémentation de `algorithms.bgdetect`. L'overlay est actuellement rendue avec `opacity: 1` (écart mineur vs la spec qui demande `0.5`, à corriger dans un autre change).

Pour juger visuellement la qualité de la détection, l'utilisateur veut basculer entre « montre le fond » (actuel) et « montre ce qui est préservé » (inversion) sans relancer la détection.

## Goals / Non-Goals

**Goals:**
- Permettre un toggle visuel instantané entre masque et son complément, sans appel réseau additionnel.
- Persister l'état du toggle en `localStorage` (clé `dashBgInvert`).
- Conserver une séparation stricte visualisation / payload : `preserve_bg` envoyé à `/api/convert` reste indépendant.
- Réutiliser le blob déjà récupéré (pas de nouvel appel à `/api/bgmask`).

**Non-Goals:**
- Modifier le comportement de `preserve_bg` ou de `/api/convert` / `/api/preview`.
- Ajouter un paramètre serveur pour l'inversion (option B écartée — voir Décisions).
- Changer l'opacité actuelle de l'overlay (écart distinct, scope d'un autre change).

## Decisions

**Décision 1 — Inversion côté client uniquement.**
On inverse visuellement l'overlay déjà récupérée, sans appel réseau. Deux sous-options considérées :

- **(1a) CSS `filter: invert(1)` sur `img.bg-mask-overlay`** — 1 ligne, zéro coût CPU, réversible instantanément au toggle. ✅ Choisi.
- **(1b) Post-traitement canvas : redessiner le PNG en inversant les bits** — plus flexible (permet plus tard un toggle supplémentaire « colorer le masque ») mais complexifie le cycle de vie (il faut régénérer un blob à chaque toggle). Rejeté pour cette itération.

**Rationale :** le masque rendu est du noir/blanc pur (ou alpha binaire). `filter: invert(1)` produit exactement le complément attendu. Si à l'avenir on passe à un masque coloré ou multi-classe, on rebasculera sur (1b).

**Décision 2 — Option B (paramètre serveur `invert=1` sur `/api/bgmask`) rejetée.**
Ajouterait un round-trip réseau pour chaque bascule, augmenterait la surface API sans bénéfice pour l'utilisateur (vu qu'on a déjà le masque en mémoire côté client). Conservée mentalement comme plan B si un jour le masque cesse d'être binaire.

**Décision 3 — Persistance via `localStorage.dashBgInvert`.**
Suit la convention existante (`dashLeftOpen`, `dashRightOpen`). Valeur `"true"` ou `"false"` sérialisée en string.

**Décision 4 — État disabled.**
Le toggle est `disabled` (grisé) quand :
- `activeImage === null` (aucune image sélectionnée), OU
- l'overlay `.bg-mask-overlay` n'est pas présente dans le DOM (détection pas encore lancée).

Au retrait de l'overlay (re-clic sur `🎯 Détecter fond` ou changement d'image), on remet le toggle à son état désactivé mais **on préserve sa valeur** dans `localStorage` — la prochaine détection restaurera automatiquement l'inversion si elle était active.

**Décision 5 — Emplacement UI.**
Intégrer dans le bloc bg-detect existant (même ligne visuelle que `Préserver fond`). Ordre proposé :
```
[🎯 Détecter fond] [tolérance: 8]
[ ] Préserver fond           — (Fond : #RRGGBB)
[ ] Inverser masque
```

## Risks / Trade-offs

- **Risque** : `filter: invert(1)` inverse aussi le canal alpha si l'image est RGBA et que l'alpha n'est pas binaire → artefacts de bord.
  **Mitigation** : le masque retourné par `algorithms.bgdetect.build_mask_png` est noir/blanc pur avec alpha=255 partout ; vérifier en revue. Si besoin, ajouter `filter: invert(1) contrast(1000%)` pour re-binariser.

- **Risque** : l'utilisateur active le toggle sans overlay visible → confusion (rien ne change).
  **Mitigation** : le toggle est `disabled` quand pas d'overlay. Persistance du choix pour le prochain cycle de détection.

- **Risque** : mémoire `localStorage` non disponible (mode privé navigateur).
  **Mitigation** : try/catch autour des `localStorage.setItem/getItem`, fallback sur variable in-memory — pattern déjà utilisé dans le dashboard actuel (voir `toggleLeftPanel`).

- **Trade-off** : pas d'inversion serveur = pas de cache serveur du masque inversé. Acceptable car `filter: invert` est quasi-gratuit.
