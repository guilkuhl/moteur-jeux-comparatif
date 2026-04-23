import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
import { api } from '@/api/client';
import type { ServerCapabilities } from '@/types/api';

const USE_GPU_KEY = 'pixel-lab:use-gpu';

export const useCapabilitiesStore = defineStore('capabilities', () => {
  const data = ref<ServerCapabilities | null>(null);
  const loading = ref(false);
  const useGpu = ref<boolean>(localStorage.getItem(USE_GPU_KEY) === '1');

  watch(useGpu, (v) => {
    localStorage.setItem(USE_GPU_KEY, v ? '1' : '0');
  });

  async function refresh(): Promise<void> {
    loading.value = true;
    try {
      data.value = await api.getCapabilities();
      // Si le GPU n'est pas dispo, on désactive d'office le toggle côté client
      if (!data.value.gpu.available) useGpu.value = false;
    } catch {
      data.value = null;
    } finally {
      loading.value = false;
    }
  }

  return { data, loading, useGpu, refresh };
});
