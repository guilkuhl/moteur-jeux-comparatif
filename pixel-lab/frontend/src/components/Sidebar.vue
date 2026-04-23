<script setup lang="ts">
import { onMounted } from 'vue';
import { useImagesStore } from '@/stores/images';

const images = useImagesStore();
onMounted(() => void images.refresh());

async function onUpload(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  try {
    await images.upload(file);
  } catch (e) {
    console.error('upload failed', e);
  } finally {
    input.value = '';
  }
}
</script>

<template>
  <aside class="sidebar">
    <header>
      <h2>Images</h2>
      <label class="upload-btn">
        + Upload
        <input type="file" accept="image/*" @change="onUpload" />
      </label>
    </header>
    <p v-if="images.error" class="err">{{ images.error }}</p>
    <ul v-if="images.files.length">
      <li
        v-for="f in images.files"
        :key="f.name"
        :class="{ active: images.activeImage === f.name }"
        @click="images.select(f.name)"
      >
        <span class="name">{{ f.name }}</span>
        <span class="pill" :class="{ ok: f.processed }">{{ f.processed ? 'traitée' : 'neuf' }}</span>
      </li>
    </ul>
    <p v-else-if="!images.loading" class="muted">Aucune image dans <code>inputs/</code>.</p>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 280px; padding: 12px; border-right: 1px solid var(--border);
  background: var(--panel); overflow-y: auto;
}
header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
h2 { margin: 0; font-size: 14px; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); }
.upload-btn { cursor: pointer; padding: 4px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 12px; }
.upload-btn input { display: none; }
ul { list-style: none; padding: 0; margin: 0; }
li {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 10px; border-radius: 4px; cursor: pointer; margin-bottom: 2px;
  font-size: 13px; gap: 8px;
}
li:hover { background: var(--panel-2); }
li.active { background: var(--panel-2); outline: 1px solid var(--green); }
.name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.muted { color: var(--muted); font-size: 13px; }
.err { color: var(--red); font-size: 13px; }
</style>
