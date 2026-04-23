import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/api/client';
import type { AlgosCatalog } from '@/types/api';

export const useAlgosStore = defineStore('algos', () => {
  const catalog = ref<AlgosCatalog | null>(null);
  const loading = ref(false);

  async function load(): Promise<void> {
    if (catalog.value) return;
    loading.value = true;
    try {
      catalog.value = await api.getAlgos();
    } finally {
      loading.value = false;
    }
  }

  return { catalog, loading, load };
});
