(() => {
  let stopPreview = () => {};
  function sample() {
    const url = new URL(location.href);
    const id = url.pathname === '/watch' ? url.searchParams.get('v') : url.pathname.match(/^\/shorts\/([A-Za-z0-9_-]{11})$/)?.[1];
    const video = document.querySelector('ytd-reel-video-renderer[is-active] video') || document.querySelector('#movie_player video') || document.querySelector('video');
    if (!/^[A-Za-z0-9_-]{11}$/.test(id || '') || !video || !Number.isFinite(video.duration) || video.duration <= 0) return null;
    return { video_id: id, url: `https://www.youtube.com/watch?v=${id}`, current_sec: video.currentTime, duration_sec: video.duration,
      title: document.querySelector('h1.ytd-watch-metadata')?.textContent?.trim() || document.title.replace(/ - YouTube$/, '') };
  }
  chrome.runtime.onMessage.addListener((message, sender, respond) => {
    if (sender.id !== chrome.runtime.id) return;
    if (message.type === 'sample') { respond(sample()); return; }
    if (message.type !== 'preview') return;
    const current = sample();
    if (!current || current.video_id !== message.video_id || !Number.isFinite(message.start_sec) || !Number.isFinite(message.end_sec) || !(0 <= message.start_sec && message.start_sec < message.end_sec && message.end_sec <= current.duration_sec)) {
      respond({ ok: false, error: '영상이 바뀌었습니다. 구간을 다시 선택해 주세요.' }); return;
    }
    const video = document.querySelector('ytd-reel-video-renderer[is-active] video') || document.querySelector('#movie_player video') || document.querySelector('video');
    stopPreview();
    const check = () => {
      if (sample()?.video_id !== current.video_id) stopPreview();
      else if (video.currentTime >= message.end_sec) { video.pause(); stopPreview(); }
    };
    stopPreview = () => { video.removeEventListener('timeupdate', check); document.removeEventListener('yt-navigate-finish', stopPreview); };
    video.addEventListener('timeupdate', check);
    document.addEventListener('yt-navigate-finish', stopPreview);
    video.currentTime = message.start_sec;
    video.play().then(() => respond({ ok: true }), () => { stopPreview(); respond({ ok: false, error: '영상의 재생 버튼을 눌러 주세요.' }); });
    return true;
  });
})();
