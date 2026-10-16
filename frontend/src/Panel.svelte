<script>
  import { onMount } from 'svelte';
  import { api, message } from './api.js';
  import { selectionForVideo, timeLabel } from '../../extension/shared.js';
  let selected = $state(null), configured = $state(false), code = $state('');
  let notice = $state(''), connecting = $state(false), creating = $state(false), job = $state(null);
  let interval, sampling = null;
  const valid = $derived(selected && Number.isFinite(selected.start_sec) && Number.isFinite(selected.end_sec) && selected.start_sec >= 0 && selected.start_sec < selected.end_sec && selected.end_sec <= selected.duration_sec);

  async function sample() {
    if (sampling) return sampling;
    sampling = (async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.id) { selected = null; return; }
      const current = await chrome.tabs.sendMessage(tab.id, { type: 'sample' });
      if (!current) { selected = null; return; }
      let previous = selected;
      if (!previous) try { previous = JSON.parse(sessionStorage.getItem('selection')); } catch {}
      selected = selectionForVideo(previous, { ...current, tab_id: tab.id });
      sessionStorage.setItem('selection', JSON.stringify(selected));
    } catch { selected = null; }
    finally { sampling = null; }
    })();
    return sampling;
  }
  onMount(() => {
    try { selected = JSON.parse(sessionStorage.getItem('selection')); } catch {}
    message({ type: 'connectionState' }).then(result => configured = result.configured).catch(error => notice = error.message);
    chrome.storage.local.get('lastJob').then(async stored => {
      if (stored.lastJob) try { job = await api(`/api/jobs/${stored.lastJob}`); } catch {}
    });
    sample(); interval = setInterval(sample, 700);
    return () => clearInterval(interval);
  });
  async function connect() {
    connecting = true; notice = '';
    try { await message({ type: 'connect', code }); configured = true; code = ''; }
    catch (error) { notice = error.message; }
    finally { connecting = false; }
  }
  async function mark(which) {
    const id = selected?.video_id;
    await sample();
    if (!selected || (id && selected.video_id !== id)) { notice = '영상이 바뀌었습니다. 구간을 다시 표시해 주세요.'; return; }
    selected[which] = Math.round(selected.current_sec * 1000) / 1000;
    sessionStorage.setItem('selection', JSON.stringify(selected));
  }
  async function preview() {
    try {
      const result = await chrome.tabs.sendMessage(selected.tab_id, { type: 'preview', ...selected });
      if (!result.ok) throw new Error(result.error);
    } catch (error) { notice = error.message; }
  }
  function openEditor(id) { chrome.tabs.create({ url: chrome.runtime.getURL(`editor.html?jobId=${id}`) }); }
  async function acquire() {
    if (!valid || creating) return;
    creating = true; notice = '';
    const chosen = { ...selected };
    try {
      const latest = await chrome.tabs.sendMessage(chosen.tab_id, { type: 'sample' });
      if (latest?.video_id !== chosen.video_id) throw new Error('영상이 바뀌었습니다. 구간을 다시 선택해 주세요.');
      job = await api('/api/jobs', 'POST', { video_id: chosen.video_id, url: chosen.url, start_sec: chosen.start_sec, end_sec: chosen.end_sec });
      openEditor(job.job_id);
    } catch (error) { notice = error.message; }
    finally { creating = false; }
  }
</script>

<main class="panel">
  <header><span class="brand">clipman</span><button class="text-button" onclick={() => configured = false}>연결 설정</button></header>
  {#if !configured}
    <section class="connection"><h1>보는 순간을<br>쇼츠로 담으세요.</h1><p>로컬 처리 프로그램을 열고 연결 코드를 복사해 주세요.</p>
      <label for="connection-code">연결 코드</label><textarea id="connection-code" bind:value={code} placeholder="복사한 코드를 붙여 넣으세요"></textarea>
      <button class="primary wide" disabled={connecting || !code.trim()} onclick={connect}>{connecting ? '연결하는 중' : '처리 프로그램 연결'}</button>
    </section>
  {:else}
    <div class="connection-line"><span class="dot"></span>이 기기에서 영상 처리</div>
    {#if selected}
      <section><h1 class="video-title">{selected.title}</h1><p class="muted">마음에 든 구간의 시작과 끝을 표시해 주세요.</p>
        <div class="current-time">{timeLabel(selected.current_sec)}<span>현재 재생 위치</span></div>
        <div class="two-columns"><button onclick={() => mark('start_sec')}>시작 표시</button><button onclick={() => mark('end_sec')}>끝 표시</button></div>
        <div class="selection-line"><label for="start">시작<input id="start" type="number" min="0" max={selected.duration_sec} step="0.1" bind:value={selected.start_sec}></label><span>~</span><label for="end">끝<input id="end" type="number" min="0" max={selected.duration_sec} step="0.1" bind:value={selected.end_sec}></label></div>
        {#if valid}<p class="duration">{(selected.end_sec - selected.start_sec).toFixed(1)}초 선택됨</p>{:else}<p class="muted">시작보다 뒤에 있는 끝 위치를 선택해 주세요.</p>{/if}
        <button class="wide" disabled={!valid} onclick={preview}>선택 구간 다시 보기</button>
        <button class="primary wide" disabled={!valid || creating} onclick={acquire}>{creating ? '구간을 준비하는 중' : '이 구간 편집하기'}</button>
      </section>
    {:else}<section class="empty"><h1>YouTube 영상을<br>열어 주세요.</h1><p>영상을 재생한 뒤 시작과 끝을 표시하면 이곳에서 바로 편집할 수 있습니다.</p></section>{/if}
    {#if job}<div class="last-job"><span>이전에 선택한 구간</span><button class="text-button" onclick={() => openEditor(job.job_id)}>편집 이어가기</button></div>{/if}
  {/if}
  {#if notice}<p class="error" role="alert">{notice}</p>{/if}
</main>
