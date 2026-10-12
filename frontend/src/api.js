export async function message(value) {
  const result = await chrome.runtime.sendMessage(value);
  if (!result?.ok) throw new Error(result?.error || '확장을 다시 열어 주세요.');
  return result.data;
}
export function api(path, method = 'GET', body) { return message({ type: 'api', path, method, body }); }
