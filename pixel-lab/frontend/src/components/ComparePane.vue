<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useImagesStore } from '@/stores/images';
import { usePreviewStore } from '@/stores/preview';

type CompareMode = 'side' | 'split' | 'diff';

interface Sample {
  x: number;
  y: number;
  src?: [number, number, number, number];
  prev?: [number, number, number, number];
}

const images = useImagesStore();
const preview = usePreviewStore();

const mode = ref<CompareMode>('side');
const splitPos = ref(0.5); // 0..1 : fraction de la largeur affichant le preview
const sample = ref<Sample | null>(null);

const sourceUrl = computed(() => {
  if (!images.activeImage) return null;
  return `/inputs/${encodeURIComponent(images.activeImage)}`;
});

const previewLabel = computed(() => {
  if (!preview.lastMeta) return '';
  const m = preview.lastMeta;
  const cache = m.cacheHitDepth > 0 ? ` · cache ${m.cacheHitDepth}` : '';
  return `${m.width}×${m.height} · ${m.elapsedMs} ms${cache}`;
});

// Canvas caches pour pipette et mode diff -----------------------------------

const srcCanvas = ref<HTMLCanvasElement | null>(null);
const prevCanvas = ref<HTMLCanvasElement | null>(null);
const diffCanvas = ref<HTMLCanvasElement | null>(null);
const diffUrl = ref<string | null>(null);

function loadIntoCanvas(url: string): Promise<HTMLCanvasElement | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const c = document.createElement('canvas');
      c.width = img.naturalWidth;
      c.height = img.naturalHeight;
      const ctx = c.getContext('2d');
      if (!ctx) return resolve(null);
      ctx.drawImage(img, 0, 0);
      resolve(c);
    };
    img.onerror = () => resolve(null);
    img.src = url;
  });
}

function revokeDiff() {
  if (diffUrl.value) {
    try { URL.revokeObjectURL(diffUrl.value); } catch { /* best-effort */ }
    diffUrl.value = null;
  }
}

async function buildDiff(): Promise<void> {
  revokeDiff();
  const a = srcCanvas.value;
  const b = prevCanvas.value;
  if (!a || !b) return;
  const w = Math.min(a.width, b.width);
  const h = Math.min(a.height, b.height);
  if (w === 0 || h === 0) return;
  const out = document.createElement('canvas');
  out.width = w; out.height = h;
  const ctx = out.getContext('2d');
  if (!ctx) return;
  const aData = a.getContext('2d')?.getImageData(0, 0, w, h);
  const bData = b.getContext('2d')?.getImageData(0, 0, w, h);
  if (!aData || !bData) return;
  const diff = ctx.createImageData(w, h);
  for (let i = 0; i < diff.data.length; i += 4) {
    const dr = Math.abs((aData.data[i] ?? 0) - (bData.data[i] ?? 0));
    const dg = Math.abs((aData.data[i + 1] ?? 0) - (bData.data[i + 1] ?? 0));
    const db = Math.abs((aData.data[i + 2] ?? 0) - (bData.data[i + 2] ?? 0));
    const m = Math.max(dr, dg, db);
    // Rouge proportionnel à la différence, sur fond noir
    diff.data[i] = m;
    diff.data[i + 1] = 0;
    diff.data[i + 2] = 0;
    diff.data[i + 3] = 255;
  }
  ctx.putImageData(diff, 0, 0);
  diffCanvas.value = out;
  out.toBlob((blob) => {
    if (blob) diffUrl.value = URL.createObjectURL(blob);
  });
}

watch(
  [sourceUrl, () => preview.lastUrl],
  async ([src, prev]) => {
    srcCanvas.value = src ? await loadIntoCanvas(src) : null;
    prevCanvas.value = prev ? await loadIntoCanvas(prev) : null;
    if (mode.value === 'diff') await buildDiff();
  },
  { immediate: true },
);

watch(mode, async (m) => {
  if (m === 'diff') await buildDiff();
});

onBeforeUnmount(() => revokeDiff());

// Pipette -------------------------------------------------------------------

function pickAt(ev: MouseEvent) {
  const target = ev.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  const relX = (ev.clientX - rect.left) / rect.width;
  const relY = (ev.clientY - rect.top) / rect.height;
  const s = srcCanvas.value;
  const p = prevCanvas.value;
  // Choisit un référentiel de coordonnées : l'image préview si présente,
  // sinon la source. Les deux sont projetées en ratio 0..1.
  const ref = p ?? s;
  if (!ref) return;
  const x = Math.floor(relX * ref.width);
  const y = Math.floor(relY * ref.height);
  const srcPx = s ? readPixel(s, Math.floor(relX * s.width), Math.floor(relY * s.height)) : undefined;
  const prevPx = p ? readPixel(p, x, y) : undefined;
  const next: Sample = { x, y };
  if (srcPx) next.src = srcPx;
  if (prevPx) next.prev = prevPx;
  sample.value = next;
}

function readPixel(c: HTMLCanvasElement, x: number, y: number): [number, number, number, number] | undefined {
  if (x < 0 || y < 0 || x >= c.width || y >= c.height) return undefined;
  const ctx = c.getContext('2d');
  if (!ctx) return undefined;
  const d = ctx.getImageData(x, y, 1, 1).data;
  return [d[0] ?? 0, d[1] ?? 0, d[2] ?? 0, d[3] ?? 0];
}

function hex(rgba: [number, number, number, number]): string {
  const [r, g, b] = rgba;
  return '#' + [r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('');
}

// Split divider drag --------------------------------------------------------

const splitEl = ref<HTMLDivElement | null>(null);

function onDividerDown(ev: PointerEvent) {
  if (!splitEl.value) return;
  const el = splitEl.value;
  el.setPointerCapture(ev.pointerId);
  const move = (e: PointerEvent) => {
    const rect = el.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    splitPos.value = Math.max(0, Math.min(1, x));
  };
  const up = () => {
    el.removeEventListener('pointermove', move);
    el.removeEventListener('pointerup', up);
    el.removeEventListener('pointercancel', up);
  };
  el.addEventListener('pointermove', move);
  el.addEventListener('pointerup', up);
  el.addEventListener('pointercancel', up);
}
</script>

<template>
  <section class="compare">
    <header class="mode-bar">
      <div class="mode-switch" role="tablist" aria-label="Mode de comparaison">
        <button
          v-for="m in (['side', 'split', 'diff'] as CompareMode[])"
          :key="m"
          type="button"
          role="tab"
          :aria-selected="mode === m"
          :class="{ active: mode === m }"
          @click="mode = m"
        >
          {{ m === 'side' ? 'Côte à côte' : m === 'split' ? 'Split' : 'Diff' }}
        </button>
      </div>
      <span v-if="sample" class="sample mono">
        <span>({{ sample.x }}, {{ sample.y }})</span>
        <span v-if="sample.src">src {{ hex(sample.src) }}</span>
        <span v-if="sample.prev">prev {{ hex(sample.prev) }}</span>
      </span>
      <span v-if="preview.status === 'inflight'" class="pill run">calcul…</span>
      <span v-else-if="preview.status === 'error'" class="pill err">erreur</span>
      <span v-else-if="preview.lastMeta" class="sub">{{ previewLabel }}</span>
    </header>

    <div v-if="mode === 'side'" class="grid-2">
      <div class="pane">
        <div class="pane-label">Source · {{ images.activeImage ?? '—' }}</div>
        <div class="img-box" @mousemove="pickAt" @mouseleave="sample = null">
          <img v-if="sourceUrl" :src="sourceUrl" :alt="images.activeImage ?? 'source'" />
          <p v-else class="muted">Aucune image sélectionnée</p>
        </div>
      </div>
      <div class="pane">
        <div class="pane-label">Preview</div>
        <div class="img-box" @mousemove="pickAt" @mouseleave="sample = null">
          <img v-if="preview.lastUrl" :src="preview.lastUrl" alt="preview" />
          <p v-else-if="!preview.liveMode" class="muted">Active <code>Live preview</code> pour voir le rendu.</p>
          <p v-else-if="preview.errorMsg" class="err">{{ preview.errorMsg }}</p>
          <p v-else class="muted">Construis un pipeline pour déclencher le preview.</p>
        </div>
      </div>
    </div>

    <div v-else-if="mode === 'split'" class="split-root" ref="splitEl" @mousemove="pickAt" @mouseleave="sample = null">
      <img v-if="sourceUrl" class="split-img" :src="sourceUrl" alt="source" />
      <img
        v-if="preview.lastUrl"
        class="split-img overlay"
        :style="{ clipPath: `inset(0 ${(1 - splitPos) * 100}% 0 0)` }"
        :src="preview.lastUrl"
        alt="preview"
      />
      <div
        v-if="sourceUrl && preview.lastUrl"
        class="divider"
        :style="{ left: `${splitPos * 100}%` }"
        @pointerdown="onDividerDown"
        role="separator"
        aria-orientation="vertical"
      />
      <p v-if="!sourceUrl" class="muted centered">Aucune image sélectionnée</p>
      <p v-else-if="!preview.lastUrl" class="muted centered">Preview non disponible — active live preview ou construis un pipeline.</p>
    </div>

    <div v-else class="diff-root" @mousemove="pickAt" @mouseleave="sample = null">
      <img v-if="diffUrl" class="split-img" :src="diffUrl" alt="diff source / preview" />
      <p v-else class="muted centered">Source et preview requis pour calculer la différence.</p>
    </div>
  </section>
</template>

<style scoped>
.compare { flex: 1; display: flex; flex-direction: column; min-width: 0; background: var(--bg); }
.mode-bar {
  padding: 6px 12px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
.mode-switch { display: inline-flex; gap: 0; border-radius: 6px; overflow: hidden; border: 1px solid var(--border); }
.mode-switch button { border-radius: 0; border: 0; padding: 4px 10px; font-size: 12px; background: var(--panel); }
.mode-switch button.active { background: var(--green); color: var(--green-fg); }
.sample { display: inline-flex; gap: 10px; font-size: 11px; color: var(--muted); }
.sub { font-size: 12px; color: var(--muted); margin-left: auto; }
.pill { margin-left: auto; }

.grid-2 { flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: var(--border); min-height: 0; }
.pane { display: flex; flex-direction: column; min-width: 0; min-height: 0; background: var(--bg); }
.pane-label { padding: 6px 12px; font-size: 11px; color: var(--muted); border-bottom: 1px solid var(--border); text-transform: uppercase; letter-spacing: .04em; }
.img-box { flex: 1; display: grid; place-items: center; padding: 16px; overflow: auto; min-height: 0; cursor: crosshair; }
.img-box img { max-width: 100%; max-height: 100%; image-rendering: pixelated; }

.split-root, .diff-root { flex: 1; position: relative; display: grid; place-items: center; padding: 16px; overflow: hidden; cursor: crosshair; }
.split-img { max-width: 100%; max-height: 100%; image-rendering: pixelated; }
.split-img.overlay { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }
.divider {
  position: absolute; top: 0; bottom: 0; width: 2px;
  background: var(--green); cursor: ew-resize;
  transform: translateX(-1px);
}
.divider::after {
  content: ''; position: absolute; top: 50%; left: 50%;
  width: 14px; height: 14px; border-radius: 50%;
  background: var(--green); transform: translate(-50%, -50%);
}

.muted { color: var(--muted); font-size: 13px; }
.centered { position: absolute; inset: 0; display: grid; place-items: center; }
.err { color: var(--red); }
</style>
