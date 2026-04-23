import { defineStore } from 'pinia';
import { ref, watch } from 'vue';

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'pixel-lab:theme';

function detectInitial(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme);
}

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>(detectInitial());
  applyTheme(theme.value);

  watch(theme, (t) => {
    applyTheme(t);
    localStorage.setItem(STORAGE_KEY, t);
  });

  function toggle(): void {
    theme.value = theme.value === 'dark' ? 'light' : 'dark';
  }

  return { theme, toggle };
});
