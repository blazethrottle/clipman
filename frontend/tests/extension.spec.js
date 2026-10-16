import { test, expect, chromium } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

test('actual MV3 extension marks a simulated YouTube page, edits and saves a real MP4', async () => {
  const context = await chromium.launchPersistentContext('', {
    channel: 'chromium', headless: true, viewport: { width: 1240, height: 880 },
    args: [`--disable-extensions-except=${resolve(process.env.CLIPMAN_EXTENSION_PATH || '../extension/dist')}`, `--load-extension=${resolve(process.env.CLIPMAN_EXTENSION_PATH || '../extension/dist')}`],
  });
  const errors = [];
  try {
    const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker');
    const id = new URL(worker.url()).hostname;
    expect(id).toBe('mclhahjlopneichbpdcclfejapcklegc');
    const youtube = await context.newPage();
    await youtube.route('https://www.youtube.com/**', route => {
      if (route.request().url().endsWith('/fixture.mp4')) {
        const data = readFileSync(resolve('../logs/browser-source.mp4'));
        const range = /bytes=(\d+)-(\d*)/.exec(route.request().headers().range || '');
        if (!range) return route.fulfill({ contentType: 'video/mp4', headers: { 'Accept-Ranges': 'bytes' }, body: data });
        const start = +range[1], end = range[2] ? +range[2] : data.length - 1;
        return route.fulfill({ status: 206, contentType: 'video/mp4', headers: { 'Accept-Ranges': 'bytes', 'Content-Range': `bytes ${start}-${end}/${data.length}` }, body: data.subarray(start, end + 1) });
      }
      return route.fulfill({ contentType: 'text/html; charset=utf-8', body: `<!doctype html><html><head><meta charset="utf-8"><title>테스트 장면 - YouTube</title></head><body><h1 class="ytd-watch-metadata">테스트 장면</h1><div id="movie_player"><video src="/fixture.mp4" preload="auto"></video></div></body></html>` });
    });
    await youtube.goto('https://www.youtube.com/watch?v=BaW_jenozKc');
    await expect.poll(() => youtube.locator('video').evaluate(video => video.readyState)).toBeGreaterThanOrEqual(2);
    const cdp = await context.newCDPSession(youtube);
    const contexts = [];
    cdp.on('Runtime.executionContextCreated', ({ context }) => contexts.push(context));
    await cdp.send('Runtime.enable');
    const panel = await context.newPage();
    panel.on('pageerror', error => errors.push(error.message));
    await panel.goto(`chrome-extension://${id}/panel.html`);
    await panel.locator('#connection-code').fill(readFileSync(resolve('../logs/browser-fixture.json'), 'utf8'));
    await panel.getByRole('button', { name: '처리 프로그램 연결', exact: true }).click();
    await expect(panel.getByText('이 기기에서 영상 처리')).toBeVisible();
    const isolated = contexts.find(context => context.name === id || context.origin === `chrome-extension://${id}`);
    expect(isolated, 'Chrome content-script isolated world').toBeTruthy();
    const keyRead = await cdp.send('Runtime.evaluate', {
      contextId: isolated.id, awaitPromise: true, returnByValue: true,
      expression: `(async()=>{try{return {readable:!!(await chrome.storage.local.get('connection')).connection}}catch{return {readable:false}}})()`,
    });
    expect(keyRead.result.value.readable).toBe(false);
    const tabId = await panel.evaluate(async () => {
      const self = await chrome.tabs.getCurrent();
      return (await chrome.tabs.query({})).find(tab => tab.index === self.index - 1).id;
    });
    await panel.evaluate(tabId => chrome.tabs.update(tabId, { active: true }), tabId);
    await expect(panel.getByRole('heading', { name: '테스트 장면' })).toBeVisible();
    await panel.getByRole('button', { name: '시작 표시', exact: true }).click();
    await youtube.evaluate(() => document.querySelector('video').currentTime = 2);
    await expect.poll(() => youtube.locator('video').evaluate(video => video.currentTime)).toBe(2);
    await panel.getByRole('button', { name: '끝 표시', exact: true }).click();
    await expect(panel.getByText('2.0초 선택됨')).toBeVisible();
    await panel.setViewportSize({ width: 380, height: 900 });
    await panel.screenshot({ path: '../logs/chrome-panel.png', fullPage: true });
    const newEditor = context.waitForEvent('page');
    await panel.getByRole('button', { name: '이 구간 편집하기' }).click();
    const editor = await newEditor;
    editor.on('pageerror', error => errors.push(error.message));
    await expect(editor.getByRole('heading', { name: '이 장면, 이 구도.' })).toBeVisible();
    await expect(editor.locator('#trim-end')).toHaveValue('2');
    await expect.poll(() => editor.locator('video').evaluate(video => video.readyState)).toBeGreaterThanOrEqual(2);
    await editor.locator('#trim-start').fill('0.25');
    await editor.locator('#trim-end').fill('1.25');
    await editor.locator('#crop').fill('100');
    await editor.reload();
    await expect(editor.locator('#trim-start')).toHaveValue('0.25');
    await expect(editor.locator('#crop')).toHaveValue('100');
    await expect.poll(() => editor.locator('video').evaluate(video => video.readyState)).toBeGreaterThanOrEqual(2);
    await editor.screenshot({ path: '../logs/chrome-editor.png', fullPage: true });
    await editor.getByRole('button', { name: '쇼츠 만들기', exact: true }).click();
    await expect(editor.getByRole('link', { name: 'MP4 저장', exact: true })).toBeVisible({ timeout: 30000 });
    const downloadEvent = editor.waitForEvent('download');
    await editor.getByRole('link', { name: 'MP4 저장', exact: true }).click();
    const download = await downloadEvent;
    expect(await download.failure()).toBeNull();
    expect(download.suggestedFilename()).toMatch(/\.mp4$/);
    await editor.getByRole('button', { name: '전체 화면 유지' }).click();
    await editor.getByRole('button', { name: '쇼츠 만들기', exact: true }).click();
    await expect(editor.getByRole('link', { name: 'MP4 저장', exact: true })).toHaveCount(2, { timeout: 30000 });
    await editor.reload();
    await expect(editor.locator('#trim-start')).toHaveValue('0.25');
    await expect(editor.getByRole('button', { name: '전체 화면 유지' })).toHaveClass(/chosen/);
    await editor.setViewportSize({ width: 430, height: 900 });
    await editor.screenshot({ path: '../logs/chrome-editor-narrow.png', fullPage: true });
    expect(await editor.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await panel.evaluate(tabId => chrome.tabs.update(tabId, { active: true }), tabId);
    await expect(panel.locator('#start')).toHaveValue('0');
    await youtube.evaluate(() => history.pushState({}, '', '/watch?v=abcdefghijk'));
    await expect(panel.locator('#start')).toHaveValue('');
    await expect(panel.getByRole('button', { name: '이 구간 편집하기' })).toBeDisabled();
    expect(errors).toEqual([]);
  } finally { await context.close(); }
});
