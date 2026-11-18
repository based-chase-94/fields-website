// Runs inside every menu board page (inlined by tools/build-screens.py).
// Scales the 3840x2160 board to the screen, plays the grass loop, keeps itself up to date,
// and keeps working from its offline cache when the store's internet drops.
//
// URL options, for testing on a TV:
//   ?video=4k     the 3840x2160 loop instead of the 1920x1080 default
//   ?video=off    the still only
//   ?check        title-safe margin, the build id and the screen's real resolution
//   ?zoom=0.5     shrink the board by this factor, for a player that shows the page zoomed
//                 in (the XOGO Minis in the store showed the middle quarter, i.e. 2x)
(() => {
  const stage = document.getElementById('stage');
  const video = document.getElementById('bg');
  const dot = document.getElementById('dot');
  const q = new URLSearchParams(location.search);
  const BUILD = stage.dataset.build;
  const POLL = 2 * 60 * 1000;

  // ---- fit the stage to the screen (any resolution, letterboxed if not 16:9)
  // Players disagree on how big the window is, so take the smallest size any of them reports.
  const zoom = Math.min(Math.max(parseFloat(q.get('zoom')) || 1, 0.1), 4);
  const view = () => {
    const vv = window.visualViewport;
    const de = document.documentElement;
    return [Math.min(innerWidth, de.clientWidth || innerWidth, vv ? vv.width : innerWidth),
            Math.min(innerHeight, de.clientHeight || innerHeight, vv ? vv.height : innerHeight)];
  };
  const fit = () => {
    const [w, h] = view();
    stage.style.transform = `scale(${Math.min(w / 3840, h / 2160) * zoom})`;
  };
  addEventListener('resize', fit);
  window.visualViewport?.addEventListener('resize', fit);
  fit();
  // Show the board once Fredoka has loaded, so a fallback face never flashes up.
  // Five seconds at most, then show it anyway.
  Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 5000))])
    .then(() => stage.classList.add('ready'));

  // ---- the grass loop. The poster still is the stage background, so a video that
  // fails, stalls or is switched off leaves the board on its still, never black.
  const want = q.get('video');
  const src = want === 'off' ? '' : (want === '4k' && stage.dataset.loopUhd) || stage.dataset.loopHd;
  if (src) {
    video.src = src;
    const play = () => video.play().catch(() => {});
    video.addEventListener('canplay', play, { once: true });
    play();
    // A stall in a web view sometimes never recovers on its own: nudge it.
    let last = -1;
    setInterval(() => {
      if (!video.paused && video.currentTime === last) { video.load(); play(); }
      last = video.currentTime;
    }, 10000);
  } else {
    video.remove();
  }

  // ---- updates. XOGO may keep the page open for days, so the page checks for a new
  // build itself and reloads at the loop's seam, where the swap can't be seen.
  let pending = false;
  const reload = () => location.reload();
  const reloadAtSeam = () => {
    if (!src || video.paused) return reload();
    let prev = video.currentTime;
    const onTime = () => {
      if (video.currentTime < prev) reload(); // wrapped back to the start
      prev = video.currentTime;
    };
    video.addEventListener('timeupdate', onTime);
    setTimeout(reload, 30000); // the loop is 18.5 s; don't wait forever
  };
  const poll = async () => {
    try {
      const r = await fetch(`../version.json?t=${Date.now()}`, { cache: 'no-store' });
      if (!r.ok) throw new Error(r.status);
      const { build } = await r.json();
      dot.classList.remove('offline');
      if (build !== BUILD && !pending) {
        pending = true;
        // Fetch the new page first, so a half-finished deploy never replaces a good board.
        const p = await fetch(location.pathname, { cache: 'no-store' });
        if (p.ok && (await p.text()).includes(`data-build="${build}"`)) reloadAtSeam();
        else pending = false;
      }
    } catch {
      dot.classList.add('offline');
    }
  };
  setInterval(poll, POLL);
  setTimeout(poll, 15000);

  // A fresh page once a night (4 AM on the player's clock) clears anything a web view
  // leaks over days of video.
  const now = new Date();
  const four = new Date(now);
  four.setHours(4, 0, 0, 0);
  if (four <= now) four.setDate(four.getDate() + 1);
  setTimeout(reload, four - now);

  // ---- offline: the service worker keeps the page, fonts, still and loop cached.
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('../sw.js', { scope: '../' }).catch(() => {});
  }

  // ---- ?check
  if (q.has('check')) {
    document.body.classList.add('check');
    const safe = document.createElement('div');
    safe.id = 'safe';
    const info = document.createElement('div');
    info.id = 'info';
    const show = () => {
      const vv = window.visualViewport;
      info.textContent = `build ${BUILD} · zoom ${zoom} · screen ${screen.width}×${screen.height} @${devicePixelRatio}x · ` +
        `window ${innerWidth}×${innerHeight} · page ${document.documentElement.clientWidth}×${document.documentElement.clientHeight}` +
        (vv ? ` · visual ${Math.round(vv.width)}×${Math.round(vv.height)} @${vv.scale}` : '') +
        ` · video ${src ? (want === '4k' ? '4K' : '1080p') : 'off'}` +
        (video.isConnected && video.videoWidth ? ` (${video.videoWidth}×${video.videoHeight})` : '') +
        ` · ${navigator.serviceWorker?.controller ? 'offline cache on' : 'no offline cache yet'}`;
    };
    // The info sits in the middle of the window, outside the board, so it stays readable
    // however much of the board the player crops.
    stage.append(safe);
    document.body.append(info);
    show();
    setInterval(show, 2000);
  }
})();
