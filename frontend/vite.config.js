import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { copyFileSync } from 'node:fs';
import { resolve } from 'node:path';

export default defineConfig({
  base: './', publicDir: false,
  plugins: [svelte(), { name: 'extension-files', closeBundle() {
    for (const file of ['manifest.json', 'background.js', 'content.js', 'shared.js', 'INSTALL.txt', 'THIRD_PARTY_NOTICES.txt']) copyFileSync(resolve('../extension', file), resolve('../extension/dist', file));
  } }],
  build: { outDir: '../extension/dist', emptyOutDir: true,
    rollupOptions: { input: { panel: resolve('panel.html'), editor: resolve('editor.html') } } },
});
