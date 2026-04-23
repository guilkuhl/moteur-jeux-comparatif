import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'node:path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:5500',
      '/healthz': 'http://127.0.0.1:5500',
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    target: 'es2022',
    reportCompressedSize: true,
  },
  test: {
    environment: 'happy-dom',
    globals: true,
  },
});
