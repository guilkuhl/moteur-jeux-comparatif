## Context

La boucle d'événements Vue 3 + Pinia est synchrone : toute mutation de store déclenche immédiatement les `watch`/`computed` abonnés, sur le main thread. Idem pour tout travail JS non découpé. Le browser ne repeint pas tant que le stack actuel n'est pas vide.

Le problème de **requêtes concurrentes** et celui du **diff sur main thread** sont deux concerns distincts avec la même solution racine : **tokens de génération** (latest-wins). On les traite séparément.

Le `AbortController` existant dans `preview.ts:57` coupe bien le `fetch`, mais n'empêche pas la promesse de résoudre juste avant l'abort (race entre le network et le signal). Un compteur monotone est plus robuste.

## Goals / Non-Goals

**Goals**
- Un drag de slider numérique ne déclenche **aucune** requête preview tant que l'utilisateur n'a pas relâché.
- Le diff sur une image 2048×2048 ne bloque **jamais** le main thread plus de ~20 ms.
- L'UI affiche toujours le résultat de la **dernière** requête lancée par l'utilisateur, jamais un résultat obsolète.

**Non-Goals**
- Pas de cache front des previews (le backend a déjà son cache LRU).
- Pas de streaming/progress partiel du preview (le backend renvoie un PNG entier).
- Pas de OffscreenCanvas (Safari <16 ne supporte pas bien ; ImageData via postMessage est suffisant).
- Pas d'optimisation du diff algorithme lui-même (la boucle pixel reste O(w×h), c'est juste déplacée).

## Decisions

### Decision 1 — `@change` + buffer local pour les inputs numériques

Actuellement : `@input="pipeline.updateParam(...)"` → chaque keystroke/wheel/drag pousse dans Pinia → `watch` déclenche `scheduleFire`.

Refactor :

```vue
<NumberInput
  :model-value="step.params[p.name] ?? p.default"
  :min="p.min" :max="p.max" :step="p.type === 'int' ? 1 : 0.1"
  @commit="(v) => pipeline.updateParam(i, p.name, v)"
/>
```

Où `NumberInput` est soit un petit composant extrait, soit inliné avec un `ref` local :

```vue
<input
  type="number"
  :min="p.min" :max="p.max" :step="..."
  :value="step.params[p.name] ?? p.default"
  @change="pipeline.updateParam(i, p.name, Number(($event.target as HTMLInputElement).value))"
/>
```

**Choix : inliner avec `@change` direct**. Pas besoin d'un composant extrait pour un changement de 3 caractères (`@input` → `@change`). `@change` sur `<input type="number">` se déclenche sur : Enter, blur, ou clic sur les spinners natifs — tous les cas où l'utilisateur "valide" sa valeur. Les wheel et drag souris sur spinners HTML natifs ne se déclenchent qu'à la fin. Pas de buffer local nécessaire, on lit `$event.target.value` au change.

**Alternative rejetée** : garder `@input` + augmenter le debounce à 500 ms. Rejetée car ça ne règle pas le cas "l'utilisateur tape un nombre à 3 chiffres" (chaque chiffre intermédiaire déclencherait un preview).

**Cas limite** : si l'utilisateur drag un slider custom (futur), on devra exposer `@commit`. Pour l'instant les inputs sont `<input type="number">` natifs, donc `@change` suffit.

### Decision 2 — `requestSeq` dans `usePreviewStore`

```ts
let requestSeq = 0;

async function fire(...) {
  requestSeq += 1;
  const mySeq = requestSeq;
  currentCtrl?.abort();
  const ctrl = new AbortController();
  currentCtrl = ctrl;
  status.value = 'inflight';
  try {
    const result = await api.postPreview(..., ctrl.signal);
    if (mySeq !== requestSeq) return;  // <-- nouveau : résultat obsolète
    revokeCurrent();
    lastUrl.value = URL.createObjectURL(result.blob);
    lastMeta.value = { ... };
    status.value = 'ready';
  } catch (e) {
    if (mySeq !== requestSeq) return;  // <-- idem pour l'état d'erreur
    if (e instanceof DOMException && e.name === 'AbortError') return;
    status.value = 'error';
    errorMsg.value = e instanceof Error ? e.message : String(e);
  }
}
```

**Garantie** : si `fire` est appelé N fois rapidement, seule la N-ième réponse peut affecter `lastUrl` / `status`. Les N-1 précédentes sont silencieusement ignorées. Combiné avec le `AbortController`, on a : abort du réseau + ignore du résultat.

### Decision 3 — Web Worker pour le diff

Fichier `src/workers/diff.worker.ts` :

```ts
interface DiffRequest {
  seq: number;
  width: number;
  height: number;
  srcBuf: ArrayBuffer;
  prevBuf: ArrayBuffer;
}

interface DiffResponse {
  seq: number;
  width: number;
  height: number;
  diffBuf: ArrayBuffer;
}

self.onmessage = (ev: MessageEvent<DiffRequest>) => {
  const { seq, width, height, srcBuf, prevBuf } = ev.data;
  const a = new Uint8ClampedArray(srcBuf);
  const b = new Uint8ClampedArray(prevBuf);
  const out = new Uint8ClampedArray(width * height * 4);
  for (let i = 0; i < out.length; i += 4) {
    const dr = Math.abs((a[i] ?? 0) - (b[i] ?? 0));
    const dg = Math.abs((a[i + 1] ?? 0) - (b[i + 1] ?? 0));
    const db = Math.abs((a[i + 2] ?? 0) - (b[i + 2] ?? 0));
    out[i] = Math.max(dr, dg, db);
    out[i + 1] = 0;
    out[i + 2] = 0;
    out[i + 3] = 255;
  }
  const resp: DiffResponse = { seq, width, height, diffBuf: out.buffer };
  (self as unknown as Worker).postMessage(resp, [out.buffer]);
};
```

Et côté `ComparePane.vue` :

```ts
import DiffWorker from '@/workers/diff.worker?worker';  // Vite syntaxe

let worker: Worker | null = null;
let diffSeq = 0;

function ensureWorker(): Worker {
  if (!worker) {
    worker = new DiffWorker();
  }
  return worker;
}

async function buildDiff(): Promise<void> {
  const a = srcCanvas.value;
  const b = prevCanvas.value;
  if (!a || !b) return;
  const w = Math.min(a.width, b.width);
  const h = Math.min(a.height, b.height);
  if (w === 0 || h === 0) return;
  const aCtx = a.getContext('2d');
  const bCtx = b.getContext('2d');
  if (!aCtx || !bCtx) return;
  const aData = aCtx.getImageData(0, 0, w, h);
  const bData = bCtx.getImageData(0, 0, w, h);

  diffSeq += 1;
  const mySeq = diffSeq;
  diffInflight.value = true;

  const res = await postToWorker(ensureWorker(), {
    seq: mySeq, width: w, height: h,
    srcBuf: aData.data.buffer,
    prevBuf: bData.data.buffer,
  });

  if (res.seq !== diffSeq) return;  // latest-wins

  const out = document.createElement('canvas');
  out.width = w; out.height = h;
  const ctx = out.getContext('2d');
  if (!ctx) return;
  ctx.putImageData(new ImageData(new Uint8ClampedArray(res.diffBuf), w, h), 0, 0);
  revokeDiff();
  diffCanvas.value = out;
  out.toBlob((blob) => {
    if (res.seq !== diffSeq) return;
    if (blob) diffUrl.value = URL.createObjectURL(blob);
  });
  diffInflight.value = false;
}
```

**Gotcha** : le `ImageData.data.buffer` ne peut pas être directement transférable car il appartient au canvas. On copie via `new Uint8ClampedArray(aData.data).buffer` et on transfère cette copie. Le surcoût d'une copie est ~1 ms par MB, négligeable vs. les 200 ms gagnés.

**Alternative rejetée** : `OffscreenCanvas` transféré au worker. Rejetée car Safari <16 ne supporte pas bien, et notre cas d'usage (lecture pixel + écriture pixel, pas de rendu GPU) ne profite pas du transfert canvas.

### Decision 4 — `loadSeq` pour `loadIntoCanvas`

Pattern identique à `requestSeq`, appliqué au chargement d'image :

```ts
let loadSeq = 0;

function loadIntoCanvas(url: string, mySeq: number, setter: (c: HTMLCanvasElement | null) => void) {
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.onload = () => {
    if (mySeq !== loadSeq) return;
    const c = document.createElement('canvas');
    c.width = img.naturalWidth;
    c.height = img.naturalHeight;
    const ctx = c.getContext('2d');
    if (!ctx) { setter(null); return; }
    ctx.drawImage(img, 0, 0);
    setter(c);
  };
  img.onerror = () => { if (mySeq === loadSeq) setter(null); };
  img.src = url;
}

watch([sourceUrl, () => preview.lastUrl], ([src, prev]) => {
  loadSeq += 1;
  const seq = loadSeq;
  if (src) loadIntoCanvas(src, seq, (c) => { srcCanvas.value = c; });
  else srcCanvas.value = null;
  if (prev) loadIntoCanvas(prev, seq, (c) => { prevCanvas.value = c; });
  else prevCanvas.value = null;
  if (mode.value === 'diff') void buildDiff();
}, { immediate: true });
```

**Note** : le même `seq` couvre src et prev car on veut cohérence de la paire affichée. Si l'utilisateur change d'image pendant qu'on charge, les deux sont invalidés.

### Decision 5 — Lifecycle du worker

Créer le worker paresseusement au premier `buildDiff()`, le garder vivant pour la durée du composant. `onBeforeUnmount` : `worker?.terminate()`.

Un seul worker suffit (une seule tâche diff à la fois). Si un nouveau diff est demandé pendant qu'un ancien tourne, le nouveau postMessage est mis en queue par le worker runtime, et `diffSeq` filtre l'ancien résultat à l'arrivée.

**Alternative rejetée** : pool de workers. Rejetée — un seul diff utilisateur à la fois, jamais en parallèle.

## Risks / Trade-offs

- **Risque** : un browser sans support Web Worker moderne (IE) → crash au `new Worker(...)`. Mitigation : la SPA est déjà Vue 3 + Vite ESM, aucun support IE. Aucune mitigation nécessaire.
- **Trade-off** : le `@change` au lieu de `@input` perd le "feedback live" sur la valeur tapée. Atténuation : `@change` se déclenche au blur/Enter/spinner, donc l'utilisateur a un feedback clair à chaque commit. Pour les sliders numériques natifs, les spinners n'émettent `change` qu'à la fin d'un drag, ce qui est le comportement attendu.
- **Risque** : le worker ajoute une légère latence fixe (~1-3 ms de postMessage/copy) même pour de petites images. Négligeable.

## Migration Plan

Pas de migration. Les tests vitest existants doivent continuer à passer. Ajouts :
- `stores/preview.test.ts` : cas "deux fires en succession rapide → seule la seconde publie".
- Test visuel manuel : tweaker un slider numérique via les spinners, vérifier qu'un seul preview part.
- Test visuel manuel : charger une image 2048×2048, basculer en mode diff, vérifier que la sidebar reste réactive pendant le calcul (avant fix : freeze ~1 s).

## Open Questions

Aucune.
