import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/api/client';
import type { InputFile } from '@/types/api';

export const useImagesStore = defineStore('images', () => {
  const files = ref<InputFile[]>([]);
  const activeImage = ref<string | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function refresh(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      files.value = await api.listInputs();
      // si l'image active n'existe plus, déselectionner
      if (activeImage.value && !files.value.some((f) => f.name === activeImage.value)) {
        activeImage.value = null;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  function select(name: string | null): void {
    activeImage.value = name;
  }

  async function upload(file: File): Promise<void> {
    await api.uploadInput(file);
    await refresh();
  }

  async function remove(name: string): Promise<void> {
    await api.deleteInput(name);
    if (activeImage.value === name) activeImage.value = null;
    await refresh();
  }

  return { files, activeImage, loading, error, refresh, select, upload, remove };
});
