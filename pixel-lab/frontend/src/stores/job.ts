import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { api } from '@/api/client';
import type { PipelineStep } from '@/types/api';
import type { SSEEvent } from '@/types/sse';

export const useJobStore = defineStore('job', () => {
  const activeJobId = ref<string | null>(null);
  const events = ref<SSEEvent[]>([]);
  const runningImage = ref<string | null>(null);
  const currentStep = ref<number>(-1);
  const errors = ref<{ image: string; step: number; stderr: string }[]>([]);
  const warnings = ref<string[]>([]);
  const done = ref(false);

  async function start(
    images: string[],
    pipeline: PipelineStep[],
    opts?: { useGpu?: boolean },
  ): Promise<void> {
    if (activeJobId.value) {
      throw new Error('Un job est déjà actif');
    }
    events.value = [];
    errors.value = [];
    warnings.value = [];
    done.value = false;
    runningImage.value = null;
    currentStep.value = -1;

    const res = await api.startConvert({ images, pipeline, use_gpu: opts?.useGpu ?? false });
    activeJobId.value = res.job_id;
  }

  function handle(evt: SSEEvent): void {
    events.value.push(evt);
    switch (evt.type) {
      case 'step_start':
        runningImage.value = evt.image;
        currentStep.value = evt.step;
        break;
      case 'step_error':
        errors.value.push({ image: evt.image, step: evt.step, stderr: evt.stderr });
        break;
      case 'warning':
        warnings.value.push(evt.message);
        break;
      case 'done':
        done.value = true;
        activeJobId.value = null;
        currentStep.value = -1;
        runningImage.value = null;
        break;
    }
  }

  const hasErrors = computed(() => errors.value.length > 0);
  const isRunning = computed(() => activeJobId.value !== null && !done.value);

  return { activeJobId, events, runningImage, currentStep, errors, warnings, done, hasErrors, isRunning, start, handle };
});
