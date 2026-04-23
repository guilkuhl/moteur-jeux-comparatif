import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/api/client';
import type { PipelineStep, Preset } from '@/types/api';

export const usePresetsStore = defineStore('presets', () => {
  const items = ref<Preset[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function refresh(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      items.value = await api.listPresets();
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  async function save(name: string, pipeline: PipelineStep[]): Promise<void> {
    error.value = null;
    try {
      await api.savePreset(name, pipeline);
      await refresh();
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
      throw e;
    }
  }

  async function remove(name: string): Promise<void> {
    error.value = null;
    try {
      await api.deletePreset(name);
      await refresh();
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  function find(name: string): Preset | undefined {
    return items.value.find((p) => p.name === name);
  }

  return { items, loading, error, refresh, save, remove, find };
});
