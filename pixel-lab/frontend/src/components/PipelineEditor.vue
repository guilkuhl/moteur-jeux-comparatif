<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useAlgosStore } from '@/stores/algos';
import { usePipelineStore } from '@/stores/pipeline';
import type { Algo } from '@/types/api';

const algos = useAlgosStore();
const pipeline = usePipelineStore();

onMounted(() => void algos.load());

const algoNames = computed<Algo[]>(() =>
  algos.catalog ? (Object.keys(algos.catalog) as Algo[]) : [],
);

function methodsFor(algo: Algo): string[] {
  const block = algos.catalog?.[algo];
  return block ? Object.keys(block.methods) : [];
}

function paramsFor(algo: Algo, method: string) {
  return algos.catalog?.[algo]?.methods[method]?.params ?? [];
}

function onAddStep() {
  const first = algoNames.value[0];
  if (!first) return;
  const method = methodsFor(first)[0] ?? '';
  const defaults = Object.fromEntries(paramsFor(first, method).map((p) => [p.name, p.default]));
  pipeline.addStep(first, method, defaults);
}

function onChangeMethod(i: number, newAlgo: Algo, newMethod: string) {
  pipeline.setMethod(i, newAlgo, newMethod);
  const defaults = Object.fromEntries(paramsFor(newAlgo, newMethod).map((p) => [p.name, p.default]));
  for (const [k, v] of Object.entries(defaults)) pipeline.updateParam(i, k, v as number | boolean);
}
</script>

<template>
  <div class="pipeline-editor">
    <div class="steps">
      <div v-for="(step, i) in pipeline.steps" :key="i" class="step">
        <div class="step-header">
          <span class="index">{{ i + 1 }}.</span>
          <select
            :value="step.algo"
            @change="onChangeMethod(i, ($event.target as HTMLSelectElement).value as Algo, methodsFor(($event.target as HTMLSelectElement).value as Algo)[0] ?? '')"
          >
            <option v-for="a in algoNames" :key="a" :value="a">{{ a }}</option>
          </select>
          <select
            :value="step.method"
            @change="onChangeMethod(i, step.algo, ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="m in methodsFor(step.algo)" :key="m" :value="m">{{ m }}</option>
          </select>
          <button class="danger" @click="pipeline.removeStep(i)" :aria-label="`Supprimer étape ${i + 1}`">×</button>
        </div>
        <div v-if="paramsFor(step.algo, step.method).length" class="params">
          <label v-for="p in paramsFor(step.algo, step.method)" :key="p.name" class="param">
            <span>{{ p.name }}</span>
            <input
              v-if="p.type === 'bool'"
              type="checkbox"
              :checked="!!step.params[p.name]"
              @change="pipeline.updateParam(i, p.name, ($event.target as HTMLInputElement).checked)"
            />
            <input
              v-else
              type="number"
              :min="p.min"
              :max="p.max"
              :step="p.type === 'int' ? 1 : 0.1"
              :value="step.params[p.name] ?? p.default"
              @input="pipeline.updateParam(i, p.name, Number(($event.target as HTMLInputElement).value))"
            />
          </label>
        </div>
      </div>
    </div>
    <button @click="onAddStep" :disabled="algoNames.length === 0">+ Ajouter étape</button>
  </div>
</template>

<style scoped>
.pipeline-editor { display: flex; flex-direction: column; gap: 8px; }
.steps { display: flex; flex-direction: column; gap: 6px; }
.step { border: 1px solid var(--border); border-radius: 6px; padding: 8px; background: var(--panel-2); }
.step-header { display: flex; align-items: center; gap: 6px; }
.index { color: var(--muted); min-width: 18px; }
.step-header select { flex: 1; }
.params { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 8px; }
.param { display: flex; align-items: center; gap: 4px; font-size: 12px; }
.param input[type="number"] { width: 70px; }
</style>
