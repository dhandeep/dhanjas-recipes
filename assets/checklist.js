// Tick off instructions while cooking. Every night-prep, step and toddler line gets
// a checkbox; tapping anywhere on the line ticks it (big target with messy hands).
// Ticks are remembered per recipe in this browser, and "Clear ticks" in the top bar
// resets them. The recipe markup itself is untouched — this only adds the boxes.
(function () {
  const lines = [...document.querySelectorAll('.night-prep li, .steps-block .step li, .steps-block .toddler-box li')];
  if (!lines.length) return;

  const key = 'dhanjas:ticks:' + location.pathname.split('/').pop().replace(/\.html$/, '');
  const load = () => { try { return new Set(JSON.parse(localStorage.getItem(key) || '[]')); } catch (e) { return new Set(); } };
  const save = s => { try { s.size ? localStorage.setItem(key, JSON.stringify([...s])) : localStorage.removeItem(key); } catch (e) { /* private mode */ } };
  const done = load();

  const nav = document.querySelector('.site-nav');
  const bar = document.createElement('div');
  bar.className = 'tick-status';
  bar.innerHTML = '<span class="tick-count" aria-live="polite"></span><button type="button" class="tick-clear">Clear ticks</button>';
  if (nav) nav.insertBefore(bar, nav.querySelector('.site-nav-cat'));
  const count = bar.querySelector('.tick-count');

  function refresh() {
    bar.hidden = done.size === 0;
    count.textContent = `✓ ${done.size} of ${lines.length}`;
    save(done);
  }

  lines.forEach((li, i) => {
    const box = document.createElement('input');
    box.type = 'checkbox';
    box.className = 'tick';
    box.setAttribute('aria-label', 'Done: ' + li.textContent.trim());
    li.classList.add('cl');
    li.prepend(box);
    const set = on => {
      box.checked = on;
      li.classList.toggle('done', on);
      on ? done.add(i) : done.delete(i);
    };
    set(done.has(i));
    box.addEventListener('change', () => { set(box.checked); refresh(); });
    li.addEventListener('click', e => {
      if (e.target === box || getSelection().toString()) return; // the box handles itself; let people select text
      set(!box.checked);
      refresh();
    });
  });

  bar.querySelector('.tick-clear').addEventListener('click', () => {
    lines.forEach(li => { li.classList.remove('done'); li.querySelector('.tick').checked = false; });
    done.clear();
    refresh();
  });
  refresh();
})();
