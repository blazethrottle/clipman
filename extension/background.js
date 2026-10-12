import { connection, allowedRequest } from './shared.js';

const privateStorage = chrome.storage.local.setAccessLevel({ accessLevel: 'TRUSTED_CONTEXTS' });

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});

async function request(config, method, path, body) {
  if (!allowedRequest(method, path)) throw new Error('허용되지 않은 작업입니다.');
  let response;
  try {
    response = await fetch(config.baseUrl + path, {
      method, headers: { 'X-Clipman-Token': config.token, 'X-Clipman-Extension': chrome.runtime.id, 'Content-Type': 'application/json' },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }), signal: AbortSignal.timeout(15000),
    });
  } catch { throw new Error('처리 프로그램을 열고 연결을 확인해 주세요.'); }
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '선택한 구간이나 입력을 확인해 주세요.');
  if (data.source_url) data.source_url = config.baseUrl + data.source_url;
  if (data.outputs) data.outputs = data.outputs.map(output => ({ ...output, url: config.baseUrl + output.url }));
  return data;
}

export async function handleMessage(message, sender) {
  await privateStorage;
  // content script와 웹 페이지에는 연결 키 및 임의 fetch 중계를 제공하지 않는다.
  if (sender.id !== chrome.runtime.id || !sender.url?.startsWith(chrome.runtime.getURL(''))) throw new Error('확장 화면에서만 실행할 수 있습니다.');
  if (message.type === 'connect') {
    const config = connection(message.code);
    await request(config, 'GET', '/api/connect');
    await chrome.storage.local.set({ connection: config });
    return { connected: true };
  }
  if (message.type === 'api') {
    const stored = await chrome.storage.local.get('connection');
    if (!stored.connection) throw new Error('로컬 처리 프로그램을 먼저 연결해 주세요.');
    const result = await request(connection(stored.connection), message.method || 'GET', message.path, message.body);
    if (message.method === 'POST' && message.path === '/api/jobs') await chrome.storage.local.set({ lastJob: result.job_id });
    return result;
  }
  if (message.type === 'connectionState') {
    return { configured: !!(await chrome.storage.local.get('connection')).connection };
  }
  throw new Error('알 수 없는 작업입니다.');
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  handleMessage(message, sender).then(data => respond({ ok: true, data }), error => respond({ ok: false, error: error.message }));
  return true;
});
