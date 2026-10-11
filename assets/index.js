// Front-page filtering. The cards are already in the HTML; this only hides,
// shows and reorders them, and keeps the filter state in the URL so a filtered
// view can be bookmarked or shared (e.g. /?cat=dal&tag=Instant%20Pot).
(function () {
  const data = JSON.parse(document.getElementById('recipe-data').textContent);
  const bySlug = new Map(data.map(r => [r.slug, r]));
  const list = document.getElementById('cards');
  const cards = [...list.children];
  const q = document.getElementById('q');
  const sort = document.getElementById('sort');
  const count = document.getElementById('count');
  const empty = document.getElementById('empty');
  const clear = document.getElementById('clear');
  const catBtns = [...document.querySelectorAll('[data-cat]')];
  const tagBtns = [...document.querySelectorAll('[data-tag]')];
  const original = cards.slice();

  const state = { cat: '', tags: new Set(), q: '', sort: 'type' };

  const params = new URLSearchParams(location.search);
  state.cat = params.get('cat') || '';
  params.getAll('tag').forEach(t => state.tags.add(t));
  state.q = params.get('q') || '';
  state.sort = params.get('sort') || 'type';
  q.value = state.q;
  sort.value = state.sort;

  const norm = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const haystack = new Map(data.map(r => [r.slug, norm([r.title, r.subtitle, r.categoryName, r.protein, ...r.tags, ...r.ingredients].join(' '))]));

  function matches(r) {
    if (state.cat && r.category !== state.cat) return false;
    const all = new Set(r.tags);
    for (const t of state.tags) if (!all.has(t)) return false;
    if (state.q) {
      const h = haystack.get(r.slug);
      if (!norm(state.q).split(/\s+/).filter(Boolean).every(w => h.includes(w))) return false;
    }
    return true;
  }

  const sorters = {
    type: null,
    az: (a, b) => a.title.localeCompare(b.title),
    new: (a, b) => (b.added || '').localeCompare(a.added || '') || a.title.localeCompare(b.title),
    quick: (a, b) => (a.minutes ?? 1e9) - (b.minutes ?? 1e9) || a.title.localeCompare(b.title),
  };

  function render() {
    const order = sorters[state.sort]
      ? original.slice().sort((x, y) => sorters[state.sort](bySlug.get(x.dataset.slug), bySlug.get(y.dataset.slug)))
      : original;
    let shown = 0;
    for (const el of order) {
      const ok = matches(bySlug.get(el.dataset.slug));
      el.hidden = !ok;
      if (ok) shown++;
      list.appendChild(el);
    }
    catBtns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.cat === state.cat)));
    tagBtns.forEach(b => b.setAttribute('aria-pressed', String(state.tags.has(b.dataset.tag))));
    // Grey out tags that would give zero results with the current filters.
    tagBtns.forEach(b => {
      if (state.tags.has(b.dataset.tag)) { b.disabled = false; return; }
      state.tags.add(b.dataset.tag);
      b.disabled = !data.some(matches);
      state.tags.delete(b.dataset.tag);
    });
    count.textContent = shown === data.length ? `${shown} recipes` : `${shown} of ${data.length} recipes`;
    empty.hidden = shown > 0;
    const filtered = state.cat || state.tags.size || state.q;
    clear.hidden = !filtered;

    const p = new URLSearchParams();
    if (state.cat) p.set('cat', state.cat);
    state.tags.forEach(t => p.append('tag', t));
    if (state.q) p.set('q', state.q);
    if (state.sort !== 'type') p.set('sort', state.sort);
    const qs = p.toString();
    history.replaceState(null, '', qs ? `?${qs}` : location.pathname);
  }

  catBtns.forEach(b => b.addEventListener('click', () => { state.cat = b.dataset.cat; render(); }));
  tagBtns.forEach(b => b.addEventListener('click', () => {
    const t = b.dataset.tag;
    state.tags.has(t) ? state.tags.delete(t) : state.tags.add(t);
    render();
  }));
  q.addEventListener('input', () => { state.q = q.value.trim(); render(); });
  sort.addEventListener('change', () => { state.sort = sort.value; render(); });
  const reset = () => { state.cat = ''; state.tags.clear(); state.q = ''; q.value = ''; render(); };
  clear.addEventListener('click', reset);
  document.querySelector('[data-clear]').addEventListener('click', reset);
  addEventListener('keydown', ev => {
    if (ev.key === '/' && document.activeElement !== q) { ev.preventDefault(); q.focus(); }
  });

  render();
})();
