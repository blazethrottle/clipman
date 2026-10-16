import { defineConfig } from '@playwright/test';
import { resolve } from 'node:path';
const python = resolve(process.platform === 'win32' ? '../backend/.venv/Scripts/python.exe' : '../backend/.venv/bin/python');
export default defineConfig({
  testDir: './tests', timeout: 60000, workers: 1,
  use: { screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  webServer: { command: `"${python}" tests/server.py`, url: 'http://127.0.0.1:9019/ready', reuseExistingServer: false, timeout: 30000 },
});
