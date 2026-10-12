export function connection(raw) {
  const value = typeof raw === 'string' ? JSON.parse(raw) : raw;
  const url = new URL(value.baseUrl);
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || !url.port || url.username || url.password || url.pathname !== '/' || url.search || url.hash || !/^[A-Za-z0-9_-]{32,128}$/.test(value.token)) {
    throw new Error('처리 프로그램에서 복사한 연결 코드를 붙여 넣어 주세요.');
  }
  return { baseUrl: url.origin, token: value.token };
}

export function allowedRequest(method, path) {
  if (method === 'GET' && path === '/api/connect') return true;
  if (method === 'POST' && path === '/api/jobs') return true;
  const match = /^\/api\/jobs\/[a-f0-9]{32}(\/export)?$/.exec(path);
  return !!match && (match[1] ? method === 'POST' : ['GET', 'DELETE'].includes(method));
}

export function selectionForVideo(previous, current) {
  const same = previous?.video_id === current.video_id && previous?.tab_id === current.tab_id;
  return { ...current, start_sec: same ? previous.start_sec : null, end_sec: same ? previous.end_sec : null };
}

export function cropGeometry(width, height, x = null, requested = 'crop') {
  if (requested === 'pad' || width * 16 <= height * 9) return { mode: 'pad', width, x: 0, maxX: 0 };
  const rawWidth = Math.floor(height * 9 / 16);
  const even = n => Math.floor(n / 2) * 2;
  const maxX = even(width - rawWidth);
  return { mode: 'crop', width: even(rawWidth), x: even(Math.max(0, Math.min(maxX, x ?? (width - rawWidth) / 2))), maxX };
}

export function timeLabel(seconds = 0) {
  const mins = Math.floor(seconds / 60);
  return `${mins}:${(seconds % 60).toFixed(1).padStart(4, '0')}`;
}
