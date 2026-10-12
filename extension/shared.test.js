import { test } from 'node:test';
import assert from 'node:assert/strict';
import { connection, allowedRequest, cropGeometry, selectionForVideo } from './shared.js';

test('connection accepts only numeric loopback and a connection key', () => {
  const token = 'a'.repeat(43);
  assert.equal(connection(JSON.stringify({ baseUrl: 'http://127.0.0.1:9000', token })).baseUrl, 'http://127.0.0.1:9000');
  for (const baseUrl of ['https://evil.test', 'http://localhost:9000', 'http://127.0.0.1.evil.test:9000', 'http://user@127.0.0.1:9000', 'http://127.0.0.1:9000/private']) {
    assert.throws(() => connection(JSON.stringify({ baseUrl, token })));
  }
});

test('worker can only call concrete clipman endpoints', () => {
  assert.ok(allowedRequest('POST', '/api/jobs'));
  assert.ok(allowedRequest('GET', '/api/jobs/' + 'a'.repeat(32)));
  for (const path of ['https://evil.test', '/api/jobs/../../secret', '/api/system/update-ytdlp', '/api/jobs?token=key']) {
    assert.equal(allowedRequest('GET', path), false);
  }
});

test('video navigation clears markers instead of combining new URL with old times', () => {
  const previous = { video_id: 'BaW_jenozKc', tab_id: 1, start_sec: 5, end_sec: 9 };
  assert.equal(selectionForVideo(previous, { video_id: 'abcdefghijk', tab_id: 1 }).start_sec, null);
  assert.equal(selectionForVideo(previous, { video_id: 'BaW_jenozKc', tab_id: 2 }).start_sec, null);
  assert.equal(selectionForVideo(previous, { video_id: 'BaW_jenozKc', tab_id: 1 }).end_sec, 9);
});

test('crop uses native pixels and even chroma alignment', () => {
  assert.deepEqual(cropGeometry(1920, 1080, 657), { mode: 'crop', width: 606, x: 656, maxX: 1312 });
  assert.equal(cropGeometry(720, 1280, 30).mode, 'pad');
  assert.equal(cropGeometry(1920, 1080, 9999).x, 1312);
});

test('content script cannot use the API bridge or change the connection', async () => {
  globalThis.chrome = { storage: { local: { setAccessLevel: async () => {} } }, sidePanel: { setPanelBehavior: async () => {} }, runtime: {
    id: 'trusted', getURL: path => 'chrome-extension://trusted/' + path, onMessage: { addListener() {} },
  } };
  const { handleMessage } = await import('./background.js');
  for (const url of ['https://www.youtube.com/watch?v=BaW_jenozKc', 'chrome-extension://trusted.evil/panel.html', undefined]) {
    await assert.rejects(handleMessage({ type: 'api', path: '/api/connect' }, { id: 'trusted', url }), /확장 화면/);
    await assert.rejects(handleMessage({ type: 'connect', code: '{}' }, { id: 'trusted', url }), /확장 화면/);
  }
});
