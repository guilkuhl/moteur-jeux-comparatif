## Context

Le Pixel Lab vient d'ouvrir, via le change `add-dashboard-conversion` (in-progress), le déclenchement de conversions depuis le navigateur. Le flux actuel est correct mais orienté "batch" : chaque clic sur `[▶ Lancer]` produit un `iter_NNN_*.png` dans `outputs/<image>/` et une entrée dans `history.json`. C'est la bonne granularité quand on a trouvé un réglage, mais c'est bruyant pendant le **tuning** des paramètres — trouver le bon `radius` pour un unsharp mask demande typiquement 5-10 essais dont un seul mérite d'être conservé.

Les 22 itérations supprimées à la main dans le `git status` courant sont symptomatiques : l'utilisateur fait déjà du tuning par essais-erreurs, mais avec un outil qui persiste tout. L'ajout d'un mode **preview volatile** sépare clairement les deux usages : exploration rapide (live) vs. résultat archivé (`/api/convert` inchangé).

Les décisions architecturales du change `add-dashboard-conversion` restent le socle de ce delta : Flask localhost-only, allow-list algos, validation params contre `PARAMS`, dashboard read-only en mode dégradé. Ce change ajoute un endpoint, une touche d'UI, mais ne modifie ni l'orchestration subprocess existante ni les CLI.

## Goals / Non-Goals

**Goals:**
- Fournir un feedback visuel en ~200-500 ms quand l'utilisateur tweake un paramètre dans le builder.
- Garder l'UI strictement non-bloquante : aucun spinner plein écran, aucun blocage d'interaction.
- Zéro pollution de `outputs/` et `history.json` pendant le tuning.
- Rendre le `[▶ Lancer]` existant sémantiquement clair : « fige cette itération pour de vrai ».
- Minimiser le coût de calcul via cache des préfixes de pipeline + downscale par défaut.
- Préserver la décision D2 du change parent (subprocess pour Convert officiel).

**Non-Goals:**
- Pas de vraie cancellation serveur côté Python — les threads vont au bout, leurs résultats sont simplement ignorés (cf. D13).
- Pas de ROI (calcul sur une sous-région de l'image) en V1 — complexité trop élevée (cf. Open Questions).
- Pas de worker persistant ou multiprocessing — un thread par requête Flask suffit à 1 utilisateur localhost.
- Pas de persistance du preview (pas de "snapshot volatil" sauvegardable ailleurs que via le bouton `[▶ Lancer]` existant).
- Pas de qualité progressive multi-passes (low-res puis high-res) — on s'appuie sur le downscale statique + toggle plein résolution.
- Pas d'extension du format de `PARAMS` (on réutilise la validation existante).

## Decisions

### D9. Import direct pour `/api/preview` vs subprocess pour `/api/convert`

**Choix :** `POST /api/preview` importe directement les modules `pixel-lab/scripts/algorithms/*.py` (`sharpen`, `scale2x`, `denoise`, `pixelsnap`) et applique les étapes en mémoire via Pillow. Le Convert officiel conserve son orchestration par `subprocess.Popen(process.py)`.

**Pourquoi :**
- Un subprocess coûte 50-100 ms juste pour le spawn Python — inacceptable à 200 ms de debounce.
- L'écriture disque par étape (création de `iter_NNN_*.png` temporaire) est gratuite en latence mais coûte en propreté : le preview **doit** être volatile.
- La décision D2 du change parent (subprocess pour Convert) visait à **éviter le drift** entre le chemin CLI et le chemin dashboard au niveau des artefacts produits. Pour le preview, il n'y a **aucun artefact**, donc rien à drifter : D2 ne s'applique pas.
- Les modules `algorithms/*.py` sont déjà purement fonctionnels (prennent `Image.Image`, retournent `Image.Image`), donc importables sans effet de bord.

**Alternatives considérées :**
- Subprocess vers un `preview.py` dédié qui encode le résultat en PNG base64 sur stdout — rejeté pour les 50-100 ms de spawn à chaque tweak.
- Worker Python persistant via stdin/stdout — complexité +++ pour gagner ~50 ms, pas rentable pour V1.

### D10. Image active distincte de la multi-sélection Convert

**Choix :** introduire un 2ᵉ état dans la sidebar : `selected` (cases à cocher, multi, alimente `/api/convert`) et `active` (image cliquée, mono, alimente `/api/preview`). L'activation se fait par clic sur la miniature ou par un bouton dédié. Un seul item peut être actif à la fois ; la classe `.active` existe déjà dans `index.html` (utilisée aujourd'hui pour la comparaison).

**Pourquoi :**
- Le tuning porte sur **une** image : appliquer le preview sur N images multiplie le coût de calcul sans apporter d'information utile pour régler les sliders.
- Découpler les deux sélections évite qu'un utilisateur qui tweake perde sa sélection batch, ou inversement.
- La classe `.active` existe déjà : on réutilise la sémantique "image sur laquelle on travaille".

**Alternatives considérées :**
- Tout fusionner (première image cochée = image de preview) — rejeté car cocher/décocher devient un déréglage involontaire.
- Dropdown dédié au preview — rejeté car redondant avec la sidebar et friction supplémentaire.

### D11. Downscale par défaut, plein résolution sur opt-in

**Choix :** par défaut, le serveur redimensionne l'image source à une longueur max de 256 px (conservation du ratio) avant d'appliquer le pipeline pour le preview. Un toggle "Taille réelle" côté UI envoie `downscale=null` dans le payload pour désactiver cette réduction.

**Pourquoi :**
- Les algos non-linéaires (denoise/nlm, bilateral avec grand rayon) ont un coût ~O(w·h) à O(w·h·k²). Réduire 1024×1024 à 256×256 = facteur 16 sur le nombre de pixels, donc ~16× plus rapide.
- Pour **régler des paramètres**, la silhouette et les tendances visuelles sont conservées à 256 px — c'est suffisant pour décider si `radius=1.2` est mieux que `radius=2.0`.
- Les algos taille-dépendants (`scale2x`, `pixelsnap/block` avec bloc de taille fixe) **mentent** à 256 px. Pour eux, le toggle plein résolution est indispensable au moment de valider.

**Caveat documenté dans l'UI :** un pictogramme d'avertissement à côté du toggle "Taille réelle" suggère de l'activer avant de cliquer sur `[▶ Lancer]` si le pipeline contient `scale2x` ou `pixelsnap/block`.

**Alternatives considérées :**
- Pas de downscale du tout — rejeté, le preview devient inutilisable sur des images 1024×1024 avec denoise/nlm (3-8 s par tweak).
- Downscale adaptatif par algo — rejeté, complexité sans gain substantiel.

### D12. Cache des préfixes de pipeline

**Choix :** cache LRU en mémoire serveur (clé = hash tuple `(image_source, step_1, step_2, ..., step_k)`, valeur = objet `Image` Pillow). Taille max 32 entrées. Chaque étape du pipeline cherche d'abord le résultat du préfixe dans le cache ; si hit, on part de là ; si miss, on calcule et on stocke.

**Pourquoi :**
- Cas typique : pipeline `[pixelsnap, denoise, sharpen]`, l'utilisateur tweake `radius` dans `sharpen`. Sans cache, 3 étapes recalculées à chaque tweak. Avec cache, seule `sharpen` est recalculée — gain 3×.
- La clé par préfixe **invalide automatiquement** les étapes aval dès qu'une étape amont change : si l'utilisateur revient sur `denoise` pour changer `size`, toutes les entrées de cache dont la clé inclut l'ancien `denoise` deviennent inaccessibles et finissent par être évincées par LRU.
- `functools.lru_cache` accepte des tuples hashables ; on sérialise le pipeline en tuple de tuples `(algo, method, tuple(sorted(params.items())))`.

**Taille max 32** : couvre ~4-5 pipelines récents × 4-6 étapes chacun. Mémoire ~ 32 × image 256² RGB = 32 × 192 KB = ~6 MB. Plafonnable sans douleur.

**Alternatives considérées :**
- Pas de cache (recalcul complet à chaque tweak) — rejeté, coût inutile.
- Cache disque — rejeté, overhead I/O > coût du calcul.
- Cache par hash de contenu de l'image source — utile si l'utilisateur change de fichier source ; géré implicitement en incluant `image_source` dans la clé (stem + mtime).

### D13. Cancellation client-side only via `AbortController`

**Choix :** côté client, chaque `fetch('/api/preview')` utilise un `AbortController`. Quand une nouvelle requête est déclenchée (debounce échu), on appelle `controller.abort()` sur la précédente puis on émet la nouvelle. Côté serveur, **aucune cancellation** : le thread Flask qui traitait la requête annulée continue jusqu'au bout et renvoie son PNG dans le vide.

**Pourquoi :**
- La vraie cancellation serveur (flag partagé, vérification dans les loops de Pillow/OpenCV) exige de modifier les modules `algorithms/*.py` pour y insérer des checks — casse la simplicité et la séparation.
- Pour un usage solo localhost, un thread gaspillé n'a aucun impact utilisateur visible (~1 s au pire, aucun impact sur la réactivité car le nouveau thread est déjà lancé en parallèle).
- En pratique le cache D12 élimine la plupart des calculs gaspillés : une requête annulée qui aboutit remplit simplement le cache avec un résultat qui servira plus tard si l'utilisateur revient à ces paramètres.

**Alternatives considérées :**
- Flag de cancellation partagé (`threading.Event`) vérifié dans les algos — demande de modifier `algorithms/*.py` ou d'enrober les appels, complexité sans gain V1.
- Queue avec un seul slot, remplacement en tête — équivalent au GC naturel de threads Python, plus complexe à coder.

### D14. Validation et sécurité identiques à `/api/convert`

**Choix :** `POST /api/preview` réutilise la fonction `validate_payload()` existante (allow-list algos, basename images, bornes `PARAMS`). La seule différence : pas de job_id / queue, réponse synchrone.

**Pourquoi :**
- Même surface d'attaque que `/api/convert` côté inputs (algo, method, params, image name). Pas de raison d'assouplir.
- Réutilisation directe de la fonction de validation, zéro duplication.

## Risks / Trade-offs

- **[Thread gaspillé côté serveur quand le client abort]** → Cf. D13. Coût accepté pour V1 (usage solo localhost). Si migration future vers multi-utilisateur, ajouter un `threading.Event` passé au loader d'algorithmes.
- **[Downscale qui ment sur algos taille-dépendants (`scale2x`, `pixelsnap/block`)]** → Toggle "Taille réelle" + pictogramme d'avertissement UI. Documenter dans l'Open Question "UX du downscale".
- **[Saturation mémoire du cache sur très grosses images]** → LRU borné à 32 entrées ; à 256² (taille downscale default) = ~6 MB total. Si toggle plein résolution est activé sur 4096² = ~32 × 50 MB = 1.6 GB — on limite à 8 entrées en mode full-res. À implémenter proprement.
- **[`image_source` change sur disque entre deux previews (utilisateur édite le fichier)]** → Clé de cache inclut `mtime` du fichier, invalidation automatique.
- **[Import direct casse la décision D2 en apparence]** → Désamorcé par D9 : D2 concernait les artefacts produits (iter / history), le preview n'en produit aucun. La séparation CLI / dashboard reste valide pour l'écriture.
- **[UI visuellement surchargée avec 2 états de sélection (cochée vs active)]** → À valider en revue. Fallback possible : n'afficher la marque "active" que quand le toggle live est ON.

## Migration Plan

Aucune migration de données. Change strictement additif :

1. Ajouter la route `POST /api/preview` dans `pixel-lab/server/app.py`.
2. Ajouter la logique cache LRU co-localisée dans `app.py` (une fonction `_apply_pipeline_cached(image_path, pipeline_tuple) → Image`).
3. Ajouter le toggle "Live preview" + logique JS associée dans `pixel-lab/dashboard/index.html`.
4. Ajouter la notion "image active" dans l'état JS de la sidebar.
5. Ajouter la zone d'affichage preview dans la zone de comparaison existante.

Rollback : retirer la route `/api/preview`, retirer le toggle et les deux blocs JS (≈250 lignes), retirer le cache. Zéro impact sur `/api/convert`, les CLI, et les specs existantes.

Déploiement : pas de déploiement — outil localhost. Le développeur tire le code, relance `python pixel-lab/server/app.py`, les endpoints sont disponibles.

## Open Questions

- **ROI (calcul sur une région)** : post-V1. Les algos non-locaux (denoise/nlm, bilateral, unsharp_mask avec grand radius) lisent des voisinages ; calculer sur une ROI exige un padding = rayon max de l'algo pour que les bords soient corrects. Code par algo (chacun connaît son rayon d'action). Ergonomie UI (rectangle à dessiner, zoom vs ROI, affichage du résultat "collé" sur l'original) reste à concevoir. Reprendre si downscale + cache s'avèrent insuffisants dans l'usage réel.
- **Qualité progressive** : envoyer d'abord un preview 128 px très rapide puis un 512 px quand l'utilisateur cesse de bouger pendant 500 ms. Intéressant mais demande une machine à états plus complexe. Reporté.
- **UX du downscale** : faut-il auto-activer le toggle "Taille réelle" quand le pipeline contient `scale2x` ou `pixelsnap/block` ? Prendre une décision en revue UI avant codage.
- **Clé de cache `image_source`** : basename + mtime suffit-il, ou faut-il un vrai hash de contenu ? `mtime` suffit en pratique et coûte zéro — retenu sauf contre-argument.
- **Taille max du cache en mode full-res** : 8 entrées proposé, à ajuster après mesures sur machine cible.
