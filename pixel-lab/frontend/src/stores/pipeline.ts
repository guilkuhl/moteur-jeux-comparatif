import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type { Algo, PipelineStep } from '@/types/api';

export const usePipelineStore = defineStore('pipeline', () => {
  const steps = ref<PipelineStep[]>([]);

  function addStep(algo: Algo, method: string, params: Record<string, number | boolean> = {}): void {
    steps.value.push({ algo, method, params });
  }

  function removeStep(index: number): void {
    steps.value.splice(index, 1);
  }

  function updateParam(index: number, key: string, value: number | boolean): void {
    const step = steps.value[index];
    if (!step) return;
    step.params = { ...step.params, [key]: value };
  }

  function setMethod(index: number, algo: Algo, method: string): void {
    const step = steps.value[index];
    if (!step) return;
    step.algo = algo;
    step.method = method;
    step.params = {};
  }

  function reset(): void {
    steps.value = [];
  }

  const isEmpty = computed(() => steps.value.length === 0);

  return { steps, addStep, removeStep, updateParam, setMethod, reset, isEmpty };
});
