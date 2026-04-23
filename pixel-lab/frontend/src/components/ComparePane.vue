<script setup lang="ts">
import { computed } from 'vue';
import { useImagesStore } from '@/stores/images';
import { usePreviewStore } from '@/stores/preview';

const images = useImagesStore();
const preview = usePreviewStore();

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
</script>

<template>
  <section class="compare">
    <div class="pane left">
      <header>
        <span class="label">Source</span>
        <span class="sub">{{ images.activeImage ?? '—' }}</span>
      </header>
      <div class="img-box">
        <img v-if="sourceUrl" :src="sourceUrl" :alt="images.activeImage ?? 'source'" />
        <p v-else class="muted">Aucune image sélectionnée</p>
      </div>
    </div>
    <div class="pane right">
      <header>
        <span class="label">Preview</span>
        <span v-if="preview.status === 'inflight'" class="pill run">calcul…</span>
        <span v-else-if="preview.status === 'error'" class="pill err">erreur</span>
        <span v-else-if="preview.lastMeta" class="sub">{{ previewLabel }}</span>
      </header>
      <div class="img-box">
        <img v-if="preview.lastUrl" :src="preview.lastUrl" alt="preview" />
        <p v-else-if="!preview.liveMode" class="muted">Active <code>Live preview</code> pour voir le rendu.</p>
        <p v-else-if="preview.errorMsg" class="err">{{ preview.errorMsg }}</p>
        <p v-else class="muted">Construis un pipeline pour déclencher le preview.</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.compare { flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: var(--border); min-width: 0; }
.pane { background: var(--bg); display: flex; flex-direction: column; min-width: 0; min-height: 0; }
header { padding: 8px 12px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.label { font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
.sub { font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }
.img-box { flex: 1; display: grid; place-items: center; padding: 16px; overflow: auto; min-height: 0; }
.img-box img { max-width: 100%; max-height: 100%; image-rendering: pixelated; }
.muted { color: var(--muted); font-size: 13px; }
.err { color: var(--red); }
</style>
