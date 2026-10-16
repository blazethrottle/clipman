<script>
  import { onMount } from 'svelte';
  import { api } from './api.js';
  import { cropGeometry, timeLabel } from '../../extension/shared.js';
  const id = new URL(location.href).searchParams.get('jobId');
  let job = $state(null), notice = $state(''), video = $state(), frame = $state();
  let start = $state(0), end = $state(0), mode = $state('crop'), x = $state(null), position = $state(0), playing = $state(false), pending = $state(false);
  let initialized = $state(false), refreshing = false, dragging;
  const meta = $derived(job?.source_meta);
  const geometry = $derived(meta ? cropGeometry(meta.width, meta.height, x, mode) : null);
  const busy = $derived(pending || ['queued', 'downloading', 'encoding'].includes(job?.status));
  const valid = $derived(meta && Number.isFinite(start) && Number.isFinite(end) && start >= 0 && start < end && end <= meta.duration);
  const sourceStyle = $derived(!meta || geometry?.mode === 'pad' ? '' : `width:${meta.width / geometry.width * 100}%;height:100%;left:${-geometry.x / geometry.width * 100}%;`);
  async function refresh() {
    if (refreshing) return;
    refreshing = true;
    try {
      job = await api(`/api/jobs/${id}`);
      if (job.source_meta && !initialized) {
        const edit = job.last_edit;
        start = edit?.trim_start ?? 0; end = edit?.trim_end ?? job.source_meta.duration;
        mode = edit?.mode ?? 'crop'; x = edit?.crop_x ?? null;
        try {
          const saved = JSON.parse(localStorage.getItem(`edit-${id}`));
          if (saved && Number.isFinite(saved.start) && Number.isFinite(saved.end) && 0 <= saved.start && saved.start < saved.end && saved.end <= job.source_meta.duration && ['crop', 'pad'].includes(saved.mode) && (saved.x === null || (Number.isFinite(saved.x) && saved.x >= 0))) {
            ({ start, end, mode, x } = saved);
          }
        } catch {}
        initialized = true;
      }
    } catch (error) { notice = error.message; }
    finally { refreshing = false; }
  }
  onMount(() => {
    if (!/^[a-f0-9]{32}$/.test(id || '')) { notice = '확장 패널에서 편집할 구간을 선택해 주세요.'; return; }
    refresh(); const interval = setInterval(refresh, 1000);
    return () => clearInterval(interval);
  });
  $effect(() => {
    if (initialized && valid) localStorage.setItem(`edit-${id}`, JSON.stringify({ start, end, mode, x }));
  });
  async function togglePlay() {
    if (!video || !valid) return;
    try {
      if (video.paused) { if (video.currentTime < start || video.currentTime >= end) video.currentTime = start; await video.play(); }
      else video.pause();
    } catch { notice = '미리보기 영상을 재생할 수 없습니다. 연결을 확인해 주세요.'; }
  }
  function scrub(event) { if (video) video.currentTime = +event.target.value; }
  function track() { position = video.currentTime; if (position >= end && !video.paused) video.pause(); }
  function drag(event) {
    if (busy || geometry?.mode !== 'crop') return;
    dragging = { pointer: event.pointerId, client: event.clientX, x: geometry.x, cropWidth: geometry.width };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function move(event) {
    if (!dragging) return;
    x = cropGeometry(meta.width, meta.height, dragging.x - (event.clientX - dragging.client) * dragging.cropWidth / frame.clientWidth).x;
  }
  async function save() {
    if (busy || !valid) return;
    pending = true; notice = '';
    try { job = await api(`/api/jobs/${id}/export`, 'POST', { trim_start: start, trim_end: end, mode: geometry.mode, crop_x: geometry.mode === 'crop' ? geometry.x : null }); }
    catch (error) { notice = error.message; }
    finally { pending = false; }
  }
  async function cancel() {
    pending = true;
    try { job = await api(`/api/jobs/${id}`, 'DELETE'); }
    catch (error) { notice = error.message; }
    finally { pending = false; }
  }
</script>

<svelte:window onblur={() => dragging = null}/>
<main class="editor">
  <header><span class="brand">clipman</span><span class="muted">세로 쇼츠 편집</span></header>
  {#if job}
    <div class="editor-heading"><div><h1>이 장면, 이 구도.</h1><p><a href={job.selection.url} target="_blank" rel="noreferrer">원본 영상</a> {timeLabel(job.selection.start_sec)} ~ {timeLabel(job.selection.end_sec)}</p></div><span class="status">{job.message}</span></div>
    {#if meta && job.source_url}
      <div class="workspace">
        <section class="preview-section" aria-label="세로 영상 미리보기">
          <div class="preview-stage"><div class="portrait-frame" bind:this={frame} role="presentation" onpointerdown={drag} onpointermove={move} onpointerup={() => dragging = null} onpointercancel={() => dragging = null}>
            <!-- svelte-ignore a11y_media_has_caption (원본 자막은 후속 자막 단계에서 연결한다.) -->
            <video bind:this={video} src={job.source_url} style={sourceStyle} class:pad={geometry.mode === 'pad'} preload="metadata" playsinline ontimeupdate={track} onplay={() => playing = true} onpause={() => playing = false} onerror={() => notice = '미리보기를 불러올 수 없습니다. 처리 프로그램 연결을 확인해 주세요.'}></video>
          </div></div>
          <div class="playback"><button disabled={!valid} onclick={togglePlay}>{playing ? '일시 정지' : '선택 구간 재생'}</button><span>{timeLabel(position)}</span></div>
          <label class="sr-only" for="scrub">영상 재생 위치</label><input id="scrub" class="scrubber" type="range" min="0" max={meta.duration} step="0.01" value={position} oninput={scrub}/>
        </section>
        <aside class="edit-controls"><h2>구간</h2><p class="muted">가져온 구간 안에서 더 다듬을 수 있습니다.</p>
          <div class="two-columns"><label for="trim-start">시작 (초)<input id="trim-start" type="number" min="0" max={meta.duration} step="0.1" bind:value={start} disabled={busy}></label><label for="trim-end">끝 (초)<input id="trim-end" type="number" min="0" max={meta.duration} step="0.1" bind:value={end} disabled={busy}></label></div>
          <p class="duration">{valid ? `${(end - start).toFixed(1)}초` : '시작과 끝을 확인해 주세요.'}</p>
          <h2>세로 구도</h2><div class="mode-switch"><button class:chosen={mode === 'crop'} disabled={busy} onclick={() => mode = 'crop'}>화면 채우기</button><button class:chosen={mode === 'pad'} disabled={busy} onclick={() => mode = 'pad'}>전체 화면 유지</button></div>
          {#if geometry.mode === 'crop'}<label for="crop">좌우 위치</label><input id="crop" type="range" min="0" max={geometry.maxX} step="2" value={geometry.x} disabled={busy} oninput={event => x = +event.target.value}/><div class="range-labels"><span>왼쪽</span><button class="text-button" disabled={busy} onclick={() => x = null}>가운데</button><span>오른쪽</span></div><p class="muted">미리보기 영상을 좌우로 끌어 구도를 조절하세요.</p>{:else}<p class="muted">원본 전체를 유지하고 빈 공간은 검정으로 채웁니다.</p>{/if}
          {#if !meta.has_audio}<p class="error">가져온 영상에 음성이 없습니다.</p>{/if}
          <button class="primary wide" disabled={busy || !valid} onclick={save}>{job.status === 'encoding' ? '쇼츠 만드는 중' : '쇼츠 만들기'}</button>
          {#if job.status === 'encoding'}<progress max="1" value={job.progress}></progress><button class="wide" disabled={pending} onclick={cancel}>처리 취소</button>{/if}
          {#if job.status === 'canceled'}<p class="muted">원본은 보존되었습니다. 구도를 바꿔 다시 만들 수 있습니다.</p>{/if}
          {#if job.status === 'error'}<p class="error" role="alert">{job.message}</p>{/if}
          {#if job.outputs.length}<section class="output"><h2>저장한 쇼츠</h2>{#each job.outputs as output}<a class="download" href={output.url + '&download=true'} download={output.name}>MP4 저장</a>{/each}<p class="muted">같은 원본에서 다시 만들 수 있습니다.</p></section>{/if}
        </aside>
      </div>
    {:else}<section class="waiting"><div class="waiting-frame"><span>선택한 장면을<br>가져오는 중입니다.</span></div><div><h2>{job.message}</h2><progress max="1" value={job.progress}></progress>{#if ['queued', 'downloading'].includes(job.status)}<button onclick={cancel} disabled={pending}>가져오기 취소</button>{:else}<p>Chrome 패널에서 구간을 다시 선택해 주세요.</p>{/if}</div></section>{/if}
  {:else}<section class="empty"><h1>선택한 구간을 확인하고 있습니다.</h1></section>{/if}
  {#if notice}<p class="error" role="alert">{notice}</p>{/if}
</main>
