## Context

Le pipeline actuel de Pixel Lab (`denoise`, `sharpen`, `pixelsnap`, `scale2x`) traite chaque pixel de manière homogène. Sur des sprites pixel-art où le fond est uniforme (cas fréquent : sprites exportés de Aseprite, Piskel, upscalés par ChatGPT, etc.), cela produit :

- Un **bruitage du fond** par `sharpen/unsharp_mask` à cause de l'accentuation autour des contours du sprite
- Un **blur** du fond par `denoise/bilateral` qui estompe très légèrement les zones uniformes
- Une **propagation de couleurs** du sprite vers le fond par les algos non locaux (`denoise/nlm`, `bilateral` sur grands `sigma_space`)

La plupart des sprites ont un fond soit déjà transparent (RGBA alpha=0), soit uni (noir, magenta, blanc). Le masque foreground/background est donc trivial à calculer. Une fois ce masque connu, les algos peuvent l'utiliser pour ignorer le fond et le réinjecter intact en sortie.

Contraintes :
- Réutiliser le pattern existant `algorithms/<name>.py` avec `METHODS` + `PARAMS` pour rester cohérent avec la CLI et le dashboard.
- Le masque doit être cachable et partageable entre `/api/preview` (live) et `/api/convert` (officiel) pour éviter de le recalculer à chaque étape.
- Zéro breaking change : tous les pipelines, CLI, endpoints existants doivent continuer à fonctionner sans modification.

## Goals / Non-Goals

**Goals :**
- Détection automatique du fond pour ≥95% des sprites à fond uni (y compris RGBA avec alpha=0 pré-existant).
- Endpoint de visualisation `/api/bgmask` pour inspecter le masque avant traitement.
- Paramètre `preserve_bg` activable par étape, compatible avec tous les presets existants.
- UI dashboard non intrusive (un bouton + un toggle, sans changer la structure du panneau Convertir).
- Cache du masque partagé entre preview et convert (clé sur `mtime` pour invalidation auto à l'édition source).

**Non-Goals :**
- Détection de fonds dégradés, avec texture, ou multi-couleurs (→ v2 avec K-means).
- Édition manuelle du masque dans le dashboard (pinceau, gomme) — v2.
- Antialiasing / feathering avancé du masque (V1 : masque binaire + option `feather` simple par dilatation/flou gaussien de rayon 1-5).
- Détection de multiples objets par connected components (V1 : masque binaire global).
- Support de masques alpha pré-existants **non binaires** (alpha intermédiaires). V1 traite uniquement `alpha == 0` comme fond ; les pixels avec `alpha ∈ (0, 255)` sont considérés foreground.

## Decisions

### D1 — Algorithme de détection : corner-sampling + flood-fill (vs K-means)

Lire les 4 pixels de coin. Si ≥3 sont égaux (dans la tolerance L∞), cette couleur est la bg_color. Sinon, on renvoie `None` (aucun masque appliqué, avertissement UI).

Flood-fill BFS/DFS depuis chaque pixel de bord ayant la bg_color (tolerance) → marque tous les pixels connectés comme fond. Le reste est foreground.

**Pourquoi** : 95% des sprites pixel-art ont un fond uni. Implémentation en ~50 lignes numpy (BFS itératif sur une pile). K-means ajoute une dépendance, un facteur 10× en perf, et ouvre la porte à des faux positifs (un gros aplat de couleur dans le sprite pourrait être confondu avec le fond).

**Alternative rejetée** : K-means → garder pour v2 quand on aura un vrai besoin (fonds dégradés).

**Alternative rejetée** : détection de dominant color global (sans connectivité) → rejeté car un sprite avec beaucoup de rouge uniforme pourrait voir son intérieur confondu avec le fond.

### D2 — Cache du masque

Clé : `(basename, mtime_ns, tolerance, feather)`. Stockage dans un `OrderedDict` LRU de capacité 32 (même pattern que le cache `/api/preview`). Valeur : numpy bool array H×W.

**Pourquoi** : le masque est réutilisé entre previews successifs (même image) et entre preview et convert officiel. Le calcul coûte ~10-30 ms sur 512×512, négligeable en absolu mais additif si on le refait à chaque étape du pipeline qui utilise `preserve_bg`.

**Invalidation** : automatique par `mtime`, comme pour le cache de pipeline existant. Si l'utilisateur édite `sprite.png` dans Aseprite, le prochain appel recalcule.

### D3 — Intégration aux algos : paramètre `preserve_bg` vs nouvelle étape dédiée

Option A (retenue) : ajouter `preserve_bg: bool` aux PARAMS de chaque méthode de `denoise` et `sharpen`. La fonction wrapper devient :

```python
def sharpen_with_bg(img, preserve_bg=False, **params):
    out = _original_sharpen(img, **params)
    if preserve_bg:
        mask = compute_bg_mask(img)  # cached
        out = composite(out, img, mask)  # True=foreground→out, False=bg→img
    return out
```

Option B (rejetée) : nouvelle étape `bgmask` à insérer dans le pipeline avec des méthodes `apply_before` / `apply_after`. Complexifie le modèle du pipeline (étape qui affecte les autres) et casse la linéarité actuelle (chaque étape = fonction pure `img → img`).

**Pourquoi A** : préserve le modèle mental du pipeline (étape = fonction pure), reste activable par étape (on peut vouloir preserve_bg sur denoise mais pas sur sharpen), et rétrocompatible (default False).

### D4 — Format du masque exposé via /api/bgmask

PNG avec canal alpha : alpha=0 pour fond, alpha=255 pour foreground, RGB = couleur de fond détectée (ou noir si alpha=0). Retourné en réponse binaire `image/png`.

**Pourquoi** : format universel, visualisable dans le navigateur via `<img>`, superposable dans le dashboard avec `opacity: 0.5`. Pas besoin d'un deuxième endpoint pour la couleur détectée — on peut lire les pixels RGB de n'importe quel pixel alpha=0 pour la retrouver.

**Alternative rejetée** : numpy pickle base64 → plus rapide à consommer côté Python mais inutile pour le dashboard (browser), et moins inspectable.

### D5 — Image RGBA avec alpha=0 pré-existant : bypass

Si `img.mode == "RGBA"` et `np.any(alpha == 0)`, considérer directement `mask = (alpha > 0)` sans appeler `detect_bg_color` ni `flood-fill`. C'est 3 lignes et évite les faux positifs sur des sprites déjà détourés proprement.

**Pourquoi** : cas trivial qui doit marcher parfaitement. Aucun risque d'erreur. Si l'utilisateur veut overrider (fond opaque qu'il veut traiter), il peut désactiver `preserve_bg`.

**Cas edge** : sprite en RGBA sans aucun alpha=0 (fond opaque même en RGBA) → tomber sur le flood-fill classique.

### D6 — Tolerance et distance de couleur

Distance L∞ (`max(|dr|, |dg|, |db|)`) sur les canaux RGB 0-255. Tolerance par défaut = 8.

**Pourquoi** : L∞ est plus intuitive que L2/ΔE pour un utilisateur pixel-art (« 8 signifie qu'un canal peut varier de ±8 »). ΔE serait correct perceptuellement mais nécessite conversion Lab et n'apporte rien sur des fonds binaires. 8 est un compromis : tolère le dithering léger et la compression JPEG/PNG sans fuiter dans le sprite.

## Risks / Trade-offs

- **[Risque] Faux positifs : sprite avec un gros aplat de couleur identique au fond** → la zone intérieure du sprite de cette couleur sera considérée foreground car non connectée aux bords (flood-fill depuis les bords). Mitigation : OK par construction grâce à la connectivité.

- **[Risque] Faux négatifs : sprite « flottant » avec fond bruité/dithering** → les 4 coins peuvent ne pas être identiques. Mitigation : si `detect_bg_color` renvoie `None`, afficher un avertissement dans le dashboard (« Fond non détecté, désactive 'Préserver le fond' ou augmente tolerance »). Le flood-fill n'est pas lancé.

- **[Risque] Performance sur grandes images** : flood-fill itératif en Python sur 4096² = ~1 s. Mitigation : V1 ne traite que les images en cache preview (downscale 256) ou en convert officiel (une seule fois par basename). Pour V1 on accepte 1 s sur gros fichiers. V2 : port en numpy vectorisé ou scipy.ndimage.label.

- **[Trade-off] `preserve_bg` ajoute un paramètre à chaque méthode** → augmente la surface d'API visible de chaque algo. Mitigation : paramètre rangé à part dans l'UI (section « Options avancées ») pour ne pas encombrer les sliders principaux. Note : à ce stade, l'UI V1 reste simple (checkbox global) et ne rend pas les `preserve_bg` par étape individuellement.

- **[Trade-off] Masque binaire sans antialiasing** → bordures crispy sur les sprites avec bords doux (rare en pixel-art). Mitigation : paramètre `feather` optionnel (0-5 px) qui fait une dilatation + flou gaussien du masque.

## Migration Plan

Aucune migration nécessaire. Le paramètre `preserve_bg` a un défaut `False`, les pipelines existants conservent leur comportement actuel. Déploiement = simple pull + restart.

## Open Questions

- **V2** : faut-il exposer `bg_color` / `tolerance` par étape plutôt qu'une seule fois globalement ? Actuellement on appelle `compute_bg_mask(img)` sans arguments côté algo (valeurs par défaut). Permettre un override par étape complexifie l'UI mais ouvre des cas d'usage (masque différent par algo).
- **V2** : antialiasing du masque par `feather > 0` nécessite de composer en float32 (soft masque) plutôt qu'en masque booléen. Impact : composition coûte plus cher. À chiffrer.
- **V2** : détecter plusieurs candidats de fond (coins différents → plusieurs clusters) et laisser l'utilisateur choisir.
