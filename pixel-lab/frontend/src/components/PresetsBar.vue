<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { usePipelineStore } from '@/stores/pipeline';
import { usePresetsStore } from '@/stores/presets';
import type { PipelineStep, Preset } from '@/types/api';

const pipeline = usePipelineStore();
const presets = usePresetsStore();
const fileInput = ref<HTMLInputElement | null>(null);
const selected = ref<string>('');
const localError = ref<string | null>(null);

onMounted(() => void presets.refresh());

const canSave = computed(() => !pipeline.isEmpty);

async function onApply() {
  const p = presets.find(selected.value);
  if (!p) return;
  pipeline.replaceAll(p.pipeline);
}

async function onSave() {
  localError.value = null;
  const name = window.prompt(
    'Nom du preset (1-40 caractères, alphanum / - / _)',
    selected.value || '',
  );
  if (!name) return;
  try {
    await presets.save(name, [...pipeline.steps]);
    selected.value = name;
  } catch (e) {
    localError.value = e instanceof Error ? e.message : String(e);
  }
}

async function onDelete() {
  if (!selected.value) return;
  if (!window.confirm(`Supprimer le preset "${selected.value}" ?`)) return;
  await presets.remove(selected.value);
  selected.value = '';
}

function onExport() {
  const p = presets.find(selected.value);
  if (!p) return;
  const blob = new Blob([JSON.stringify(p, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${p.name}.preset.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function onImportClick() {
  fileInput.value?.click();
}

async function onImportFile(ev: Event) {
  localError.value = null;
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;
  try {
    const text = await file.text();
    const data = JSON.parse(text) as Partial<Preset>;
    if (!data.name || !Array.isArray(data.pipeline)) {
      throw new Error('fichier invalide : attendu { name, pipeline }');
    }
    await presets.save(data.name, data.pipeline as PipelineStep[]);
    selected.value = data.name;
  } catch (e) {
    localError.value = e instanceof Error ? e.message : String(e);
  }
}
</script>

<template>
  <div class="presets-bar">
    <label class="label">Presets</label>
    <select v-model="selected" :disabled="presets.items.length === 0">
      <option value="">—</option>
      <option v-for="p in presets.items" :key="p.name" :value="p.name">{{ p.name }}</option>
    </select>
    <button type="button" :disabled="!selected" title="Appliquer le preset" @click="onApply">Charger</button>
    <button type="button" :disabled="!canSave" title="Sauvegarder le pipeline courant" @click="onSave">Sauver</button>
    <button type="button" class="danger" :disabled="!selected" title="Supprimer" @click="onDelete">×</button>
    <div class="io">
      <button type="button" :disabled="!selected" title="Exporter JSON" @click="onExport">⇣</button>
      <button type="button" title="Importer JSON" @click="onImportClick">⇡</button>
      <input ref="fileInput" type="file" accept="application/json,.json" hidden @change="onImportFile" />
    </div>
    <p v-if="localError || presets.error" class="err">{{ localError ?? presets.error }}</p>
  </div>
</template>

<style scoped>
.presets-bar {
  display: grid;
  grid-template-columns: auto 1fr auto auto auto auto;
  gap: 6px;
  align-items: center;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--panel-2);
  font-size: 12px;
}
.label { color: var(--muted); text-transform: uppercase; letter-spacing: .04em; font-size: 11px; }
.io { display: contents; }
.io button { padding: 4px 10px; }
select { font-size: 12px; }
button { font-size: 12px; padding: 4px 10px; }
.err { grid-column: 1 / -1; color: var(--red); margin: 0; font-size: 11px; }
</style>
