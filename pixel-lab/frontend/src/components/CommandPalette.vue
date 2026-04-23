<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useAlgosStore } from '@/stores/algos';
import { useImagesStore } from '@/stores/images';
import { usePipelineStore } from '@/stores/pipeline';
import { usePreviewStore } from '@/stores/preview';
import { useThemeStore } from '@/stores/theme';
import type { Algo } from '@/types/api';

interface Command {
  id: string;
  title: string;
  group: string;
  hint?: string;
  run: () => void | Promise<void>;
}

const algos = useAlgosStore();
const images = useImagesStore();
const pipeline = usePipelineStore();
const preview = usePreviewStore();
const theme = useThemeStore();

const open = ref(false);
const query = ref('');
const cursor = ref(0);
const inputEl = ref<HTMLInputElement | null>(null);

const commands = computed<Command[]>(() => {
  const out: Command[] = [];

  out.push({
    id: 'theme.toggle',
    title: theme.theme === 'dark' ? 'Basculer en mode clair' : 'Basculer en mode sombre',
    group: 'Affichage',
    run: () => theme.toggle(),
  });
  out.push({
    id: 'preview.live',
    title: preview.liveMode ? 'Désactiver le live preview' : 'Activer le live preview',
    group: 'Aperçu',
    run: () => preview.setLiveMode(!preview.liveMode),
  });

  out.push({
    id: 'pipeline.undo',
    title: 'Annuler la dernière action',
    group: 'Pipeline',
    hint: 'Ctrl+Z',
    run: () => pipeline.undo(),
  });
  out.push({
    id: 'pipeline.redo',
    title: 'Rétablir',
    group: 'Pipeline',
    hint: 'Ctrl+Shift+Z',
    run: () => pipeline.redo(),
  });
  out.push({
    id: 'pipeline.reset',
    title: 'Vider le pipeline',
    group: 'Pipeline',
    run: () => pipeline.reset(),
  });

  const catalog = algos.catalog;
  if (catalog) {
    for (const algoName of Object.keys(catalog) as Algo[]) {
      for (const method of Object.keys(catalog[algoName].methods)) {
        out.push({
          id: `add:${algoName}:${method}`,
          title: `Ajouter étape : ${algoName} / ${method}`,
          group: 'Ajouter étape',
          run: () => {
            const params = catalog[algoName].methods[method]?.params ?? [];
            const defaults = Object.fromEntries(params.map((p) => [p.name, p.default]));
            pipeline.addStep(algoName, method, defaults);
          },
        });
      }
    }
  }

  for (const f of images.files) {
    out.push({
      id: `select:${f.name}`,
      title: `Sélectionner : ${f.name}`,
      group: 'Images',
      run: () => images.select(f.name),
    });
  }

  return out;
});

const filtered = computed<Command[]>(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return commands.value;
  return commands.value.filter((c) => {
    const hay = `${c.title} ${c.group}`.toLowerCase();
    return q.split(/\s+/).every((tok) => hay.includes(tok));
  });
});

watch(filtered, () => {
  cursor.value = 0;
});

function show() {
  open.value = true;
  query.value = '';
  cursor.value = 0;
  void nextTick(() => inputEl.value?.focus());
}

function hide() {
  open.value = false;
}

async function runCurrent() {
  const cmd = filtered.value[cursor.value];
  if (!cmd) return;
  hide();
  await cmd.run();
}

function onGlobalKeydown(e: KeyboardEvent) {
  const mod = e.ctrlKey || e.metaKey;
  if (mod && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    open.value ? hide() : show();
    return;
  }
  if (!open.value) return;
  if (e.key === 'Escape') {
    e.preventDefault();
    hide();
  } else if (e.key === 'ArrowDown') {
    e.preventDefault();
    cursor.value = Math.min(cursor.value + 1, filtered.value.length - 1);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    cursor.value = Math.max(cursor.value - 1, 0);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    void runCurrent();
  }
}

onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown);
  // lazy-load catalog pour peupler les commandes d'ajout
  if (!algos.catalog) void algos.load();
});
onUnmounted(() => window.removeEventListener('keydown', onGlobalKeydown));
</script>

<template>
  <div v-if="open" class="palette-backdrop" @click.self="hide">
    <div class="palette" role="dialog" aria-modal="true" aria-label="Palette de commandes">
      <input
        ref="inputEl"
        v-model="query"
        type="text"
        placeholder="Rechercher une commande… (Esc pour fermer)"
        class="palette-search"
        autocomplete="off"
        spellcheck="false"
      />
      <ul class="palette-list" role="listbox">
        <li v-if="filtered.length === 0" class="palette-empty">Aucune commande</li>
        <li
          v-for="(cmd, i) in filtered"
          :key="cmd.id"
          :class="['palette-item', { active: i === cursor }]"
          role="option"
          :aria-selected="i === cursor"
          @mouseenter="cursor = i"
          @click="runCurrent()"
        >
          <span class="group">{{ cmd.group }}</span>
          <span class="title">{{ cmd.title }}</span>
          <span v-if="cmd.hint" class="hint">{{ cmd.hint }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.palette-backdrop {
  position: fixed; inset: 0; z-index: 700;
  background: var(--overlay);
  display: flex; align-items: flex-start; justify-content: center;
  padding-top: 12vh;
}
.palette {
  width: min(640px, 90vw);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow);
  overflow: hidden;
  display: flex; flex-direction: column;
}
.palette-search {
  width: 100%;
  padding: 12px 14px;
  font-size: 15px;
  background: transparent;
  border: 0; border-bottom: 1px solid var(--border);
  color: var(--text);
  border-radius: 0;
  outline: none;
}
.palette-list {
  list-style: none; margin: 0; padding: 4px;
  max-height: 50vh; overflow-y: auto;
}
.palette-empty { padding: 12px 14px; color: var(--muted); font-size: 13px; }
.palette-item {
  display: grid;
  grid-template-columns: 120px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.palette-item.active { background: var(--panel-2); outline: 1px solid var(--green); }
.palette-item .group { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
.palette-item .title { color: var(--text); }
.palette-item .hint { color: var(--muted); font-family: var(--mono); font-size: 11px; }
</style>
