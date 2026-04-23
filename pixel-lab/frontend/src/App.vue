<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import Sidebar from '@/components/Sidebar.vue';
import ComparePane from '@/components/ComparePane.vue';
import ConvertPanel from '@/components/ConvertPanel.vue';
import CommandPalette from '@/components/CommandPalette.vue';
import { usePreviewStore } from '@/stores/preview';
import { useThemeStore } from '@/stores/theme';
import { useImagesStore } from '@/stores/images';
import { useImageDrop } from '@/composables/useImageDrop';

const preview = usePreviewStore();
useThemeStore();
const images = useImagesStore();

const dropError = ref<string | null>(null);
const lastUploaded = ref<string | null>(null);

const { isDragging } = useImageDrop({
  onFiles: async (files) => {
    dropError.value = null;
    let ok = 0;
    for (const f of files) {
      try {
        await images.upload(f);
        ok += 1;
      } catch (e) {
        dropError.value = e instanceof Error ? e.message : String(e);
      }
    }
    if (ok) {
      lastUploaded.value = `${ok} image${ok > 1 ? 's' : ''} importée${ok > 1 ? 's' : ''}`;
      window.setTimeout(() => (lastUploaded.value = null), 2500);
    }
  },
});

// Healthcheck au boot, pour signaler tôt si le back est down
onMounted(async () => {
  try {
    const r = await fetch('/healthz');
    if (!r.ok) console.warn('Back unhealthy', r.status);
  } catch (e) {
    console.warn('Back unreachable', e);
  }
});

// Safety net : libérer la blob URL avant unload
onUnmounted(() => preview.revokeCurrent());
window.addEventListener('beforeunload', () => preview.revokeCurrent());
</script>

<template>
  <div class="layout">
    <Sidebar />
    <ComparePane />
    <ConvertPanel />
    <CommandPalette />
    <div v-if="isDragging" class="drop-overlay" aria-live="polite">
      <div class="drop-hint">Lâcher pour importer</div>
    </div>
    <div v-if="lastUploaded" class="toast toast-ok" role="status">{{ lastUploaded }}</div>
    <div v-if="dropError" class="toast toast-err" role="alert" @click="dropError = null">
      {{ dropError }}
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  position: relative;
}
.drop-overlay {
  position: fixed; inset: 0; z-index: 500;
  background: var(--overlay);
  display: flex; align-items: center; justify-content: center;
  pointer-events: none;
}
.drop-hint {
  padding: 16px 28px;
  border: 2px dashed var(--green);
  border-radius: 12px;
  background: var(--panel);
  color: var(--text);
  font-size: 18px; font-weight: 600;
  box-shadow: var(--shadow);
}
.toast {
  position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%);
  padding: 8px 14px; border-radius: 6px; font-size: 13px;
  box-shadow: var(--shadow);
  z-index: 600;
}
.toast-ok { background: var(--green); color: var(--green-fg); }
.toast-err { background: var(--red); color: white; cursor: pointer; }
</style>
