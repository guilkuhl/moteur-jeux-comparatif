<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useImagesStore } from '@/stores/images';
import { usePipelineStore } from '@/stores/pipeline';
import { usePreviewStore } from '@/stores/preview';
import { useJobStore } from '@/stores/job';
import { useCapabilitiesStore } from '@/stores/capabilities';
import { useSSESubscription } from '@/composables/useSSESubscription';
import PipelineEditor from './PipelineEditor.vue';
import PresetsBar from './PresetsBar.vue';

const images = useImagesStore();
const pipeline = usePipelineStore();
const preview = usePreviewStore();
const job = useJobStore();
const capabilities = useCapabilitiesStore();

onMounted(() => void capabilities.refresh());

const gpuAvailable = computed(() => capabilities.data?.gpu.available ?? false);
const gpuTooltip = computed(() => {
  if (!capabilities.data) return 'Sonde des capacités en cours…';
  const g = capabilities.data.gpu;
  if (!g.available) return 'GPU non détecté (OpenCV CUDA indisponible)';
  return `Utilise ${g.device_name ?? 'GPU'} pour les algos compatibles`;
});

const activeJobId = computed(() => job.activeJobId);
useSSESubscription(activeJobId, (evt) => {
  job.handle(evt);
  // après un job réussi, rafraîchir la sidebar pour refléter les itérations produites
  if (evt.type === 'done') void images.refresh();
});

const launchError = ref<string | null>(null);

const canLaunch = computed(() => images.activeImage && !pipeline.isEmpty && !job.isRunning);

async function onLaunch() {
  launchError.value = null;
  try {
    if (!images.activeImage) return;
    await job.start([images.activeImage], [...pipeline.steps], {
      useGpu: capabilities.useGpu && gpuAvailable.value,
    });
  } catch (e) {
    launchError.value = e instanceof Error ? e.message : String(e);
  }
}

// Live preview : re-fire dès que image active, pipeline ou toggle GPU changent (débouncé)
watch(
  [
    () => images.activeImage,
    () => pipeline.steps,
    () => preview.liveMode,
    () => preview.fullResMode,
    () => capabilities.useGpu,
  ],
  () => {
    if (!preview.liveMode) return;
    if (!images.activeImage) return;
    if (pipeline.isEmpty) return;
    preview.scheduleFire(images.activeImage, [...pipeline.steps], {
      useGpu: capabilities.useGpu && gpuAvailable.value,
    });
  },
  { deep: true },
);

function toggleLive(ev: Event) {
  preview.setLiveMode((ev.target as HTMLInputElement).checked);
  if (preview.liveMode && images.activeImage && !pipeline.isEmpty) {
    void preview.fire(images.activeImage, [...pipeline.steps], {
      useGpu: capabilities.useGpu && gpuAvailable.value,
    });
  }
}
</script>

<template>
  <section class="convert-panel">
    <header>
      <h2>Convertir</h2>
      <div class="toggles">
        <label><input type="checkbox" :checked="preview.liveMode" @change="toggleLive" /> Live preview</label>
        <label><input type="checkbox" :checked="preview.fullResMode" @change="preview.setFullResMode(($event.target as HTMLInputElement).checked)" /> Taille réelle</label>
        <label :title="gpuTooltip" :class="{ disabled: !gpuAvailable }">
          <input
            type="checkbox"
            :checked="capabilities.useGpu"
            :disabled="!gpuAvailable"
            @change="capabilities.useGpu = ($event.target as HTMLInputElement).checked"
          />
          GPU
        </label>
      </div>
    </header>

    <p v-if="!images.activeImage" class="muted">Sélectionne une image dans la sidebar.</p>

    <PresetsBar />
    <PipelineEditor />

    <footer>
      <button class="primary" :disabled="!canLaunch" @click="onLaunch">
        <span v-if="job.isRunning">Job en cours…</span>
        <span v-else>▶ Lancer</span>
      </button>
      <span v-if="launchError" class="err">{{ launchError }}</span>
    </footer>

    <div v-if="job.warnings.length" class="warnings">
      <p v-for="(w, i) in job.warnings" :key="i" class="warn">⚠ {{ w }}</p>
    </div>
    <div v-if="job.errors.length" class="errors">
      <p v-for="(e, i) in job.errors" :key="i" class="err">❌ {{ e.image }} step {{ e.step + 1 }} : {{ e.stderr }}</p>
    </div>
    <p v-if="job.runningImage" class="status">
      <span class="pill run">en cours</span> {{ job.runningImage }} · étape {{ job.currentStep + 1 }}
    </p>
    <p v-else-if="job.done" class="status">
      <span class="pill ok">done</span> {{ job.events.length }} événements reçus
    </p>
  </section>
</template>

<style scoped>
.convert-panel {
  width: 360px; padding: 16px; border-left: 1px solid var(--border);
  background: var(--panel); overflow-y: auto; display: flex; flex-direction: column; gap: 12px;
}
header { display: flex; align-items: center; justify-content: space-between; }
h2 { margin: 0; font-size: 14px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
.toggles { display: flex; gap: 12px; flex-wrap: wrap; }
.toggles label { display: flex; gap: 4px; align-items: center; font-size: 12px; }
.toggles label.disabled { opacity: .5; cursor: not-allowed; }
footer { display: flex; align-items: center; gap: 12px; }
.warnings, .errors { display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.warn { color: #f0c040; margin: 0; }
.err { color: var(--red); margin: 0; }
.status { font-size: 12px; color: var(--muted); margin: 0; display: flex; gap: 6px; align-items: center; }
.muted { color: var(--muted); font-size: 13px; margin: 0; }
</style>
