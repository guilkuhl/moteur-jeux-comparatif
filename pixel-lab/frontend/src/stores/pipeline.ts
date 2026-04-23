import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type { Algo, PipelineStep } from '@/types/api';

const HISTORY_LIMIT = 50;

function clone(steps: PipelineStep[]): PipelineStep[] {
  return steps.map((s) => ({ algo: s.algo, method: s.method, params: { ...s.params } }));
}

export const usePipelineStore = defineStore('pipeline', () => {
  const steps = ref<PipelineStep[]>([]);

  const history = ref<PipelineStep[][]>([]);
  const future = ref<PipelineStep[][]>([]);
  // Coalesce key : si deux mutations consécutives ciblent la même "unité"
  // (ex. updateParam sur (0, 'radius') pendant la frappe), on ne pousse
  // qu'un seul snapshot pour l'ensemble de l'édition.
  let lastCoalesceKey: string | null = null;

  function pushHistory(coalesceKey: string | null): void {
    if (coalesceKey !== null && coalesceKey === lastCoalesceKey) return;
    history.value.push(clone(steps.value));
    if (history.value.length > HISTORY_LIMIT) history.value.shift();
    future.value = [];
    lastCoalesceKey = coalesceKey;
  }

  function addStep(algo: Algo, method: string, params: Record<string, number | boolean> = {}): void {
    pushHistory(null);
    steps.value.push({ algo, method, params });
  }

  function removeStep(index: number): void {
    pushHistory(null);
    steps.value.splice(index, 1);
  }

  function updateParam(index: number, key: string, value: number | boolean): void {
    const step = steps.value[index];
    if (!step) return;
    pushHistory(`param:${index}:${key}`);
    step.params = { ...step.params, [key]: value };
  }

  function setMethod(index: number, algo: Algo, method: string): void {
    const step = steps.value[index];
    if (!step) return;
    pushHistory(null);
    step.algo = algo;
    step.method = method;
    step.params = {};
  }

  function reset(): void {
    pushHistory(null);
    steps.value = [];
  }

  function undo(): void {
    const prev = history.value.pop();
    if (!prev) return;
    future.value.push(clone(steps.value));
    steps.value = prev;
    lastCoalesceKey = null;
  }

  function redo(): void {
    const next = future.value.pop();
    if (!next) return;
    history.value.push(clone(steps.value));
    steps.value = next;
    lastCoalesceKey = null;
  }

  function replaceAll(next: PipelineStep[]): void {
    pushHistory(null);
    steps.value = clone(next);
  }

  const isEmpty = computed(() => steps.value.length === 0);
  const canUndo = computed(() => history.value.length > 0);
  const canRedo = computed(() => future.value.length > 0);

  return {
    steps,
    addStep,
    removeStep,
    updateParam,
    setMethod,
    reset,
    undo,
    redo,
    replaceAll,
    isEmpty,
    canUndo,
    canRedo,
  };
});
