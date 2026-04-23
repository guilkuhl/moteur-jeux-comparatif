import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/api/client';
import type { PipelineStep } from '@/types/api';

export type PreviewStatus = 'idle' | 'inflight' | 'ready' | 'error';

const DEBOUNCE_MS = 200;

export const usePreviewStore = defineStore('preview', () => {
  const liveMode = ref(false);
  const fullResMode = ref(false);
  const lastUrl = ref<string | null>(null);
  const status = ref<PreviewStatus>('idle');
  const lastMeta = ref<{ width: number; height: number; elapsedMs: number; cacheHitDepth: number } | null>(null);
  const errorMsg = ref<string | null>(null);

  let currentCtrl: AbortController | null = null;
  let debounceTimer: number | null = null;

  function revokeCurrent(): void {
    if (lastUrl.value) {
      try {
        URL.revokeObjectURL(lastUrl.value);
      } catch {
        // best-effort
      }
      lastUrl.value = null;
    }
  }

  function setLiveMode(on: boolean): void {
    liveMode.value = on;
    if (!on) {
      revokeCurrent();
      currentCtrl?.abort();
      currentCtrl = null;
      status.value = 'idle';
      lastMeta.value = null;
    }
  }

  function setFullResMode(on: boolean): void {
    fullResMode.value = on;
  }

  async function fire(image: string, pipeline: PipelineStep[]): Promise<void> {
    if (!liveMode.value) return;
    if (!image || pipeline.length === 0) {
      status.value = 'idle';
      return;
    }
    currentCtrl?.abort();
    const ctrl = new AbortController();
    currentCtrl = ctrl;
    status.value = 'inflight';
    errorMsg.value = null;

    try {
      const result = await api.postPreview(
        { image, pipeline, downscale: fullResMode.value ? null : 256 },
        ctrl.signal,
      );
      if (ctrl !== currentCtrl) return;
      revokeCurrent();
      lastUrl.value = URL.createObjectURL(result.blob);
      lastMeta.value = {
        width: result.width,
        height: result.height,
        elapsedMs: result.elapsedMs,
        cacheHitDepth: result.cacheHitDepth,
      };
      status.value = 'ready';
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return;
      status.value = 'error';
      errorMsg.value = e instanceof Error ? e.message : String(e);
    }
  }

  function scheduleFire(image: string, pipeline: PipelineStep[]): void {
    if (debounceTimer !== null) window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(() => {
      debounceTimer = null;
      void fire(image, pipeline);
    }, DEBOUNCE_MS);
  }

  return {
    liveMode,
    fullResMode,
    lastUrl,
    status,
    lastMeta,
    errorMsg,
    setLiveMode,
    setFullResMode,
    fire,
    scheduleFire,
    revokeCurrent,
  };
});
