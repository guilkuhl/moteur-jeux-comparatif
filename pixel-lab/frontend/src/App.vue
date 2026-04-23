<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import Sidebar from '@/components/Sidebar.vue';
import ComparePane from '@/components/ComparePane.vue';
import ConvertPanel from '@/components/ConvertPanel.vue';
import { usePreviewStore } from '@/stores/preview';
import { useThemeStore } from '@/stores/theme';

const preview = usePreviewStore();
useThemeStore();

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
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
</style>
