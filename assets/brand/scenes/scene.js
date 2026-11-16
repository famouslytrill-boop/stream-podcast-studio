(() => {
  const cfg = window.STREAM_BRAND || {};
  const set = (sel, value) => document.querySelectorAll(sel).forEach(el => { el.textContent = value; });
  set('[data-brand]', cfg.name || 'EmberBanter');
  set('[data-tagline]', cfg.tagline || 'Clock out. Queue up.');
  set('[data-handle]', cfg.handle ? '@' + cfg.handle.replace(/^@/,'') : 'GAMING + LIVE HANGOUTS');
  set('[data-topic]', cfg.topic || 'GOOD GAMES. BETTER COMPANY.');
  const mode = document.body.dataset.mode;
  if (cfg[mode + 'Note']) set('[data-note]', cfg[mode + 'Note']);
  const stage = document.querySelector('.stage');
  const fit = () => { stage.style.transform = `scale(${Math.min(window.innerWidth/1920, window.innerHeight/1080)})`; };
  fit(); window.addEventListener('resize', fit);
  const counter = document.querySelector('[data-count]');
  if (counter) {
    const seconds = Number.isFinite(Number(cfg.startSeconds)) ? Math.max(0,Number(cfg.startSeconds)) : 180;
    const until = Date.now() + seconds * 1000;
    const tick = () => {
      const remaining = Math.max(0, Math.ceil((until - Date.now()) / 1000));
      counter.textContent = remaining ? String(Math.floor(remaining/60)).padStart(2,'0') + ':' + String(remaining%60).padStart(2,'0') : 'READY';
      if (remaining > 0) window.setTimeout(tick, 250);
    };
    tick();
  }
})();
