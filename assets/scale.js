// Batch size: 1× / 1½× / 2× / 3×. The build computes every amount at each size in Python
// (tools/dhanjas/portions.py — toddler portions stay fixed, "rest" is recomputed) and
// stores the other sizes on <data class="q" data-x1_5 data-x2 data-x3>. This only swaps text.
// Try any recipe with ?scale=1.5 or ?scale=2.
(function () {
  const STEPS = ['1', '1.5', '2', '3'];
  const marks = [...document.querySelectorAll('data.q')];
  marks.forEach(m => { m.dataset.x1 = m.textContent; });
  const key = k => 'x' + k.replace('.', '_');

  function apply(k) {
    k = String(k);
    if (!STEPS.includes(k)) k = '1';
    for (const m of marks) m.textContent = m.dataset[key(k)] || m.dataset.x1;
    document.querySelectorAll('.scale-control [data-scale]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.scale === k)));
    document.documentElement.dataset.scale = k;
    return k;
  }

  document.querySelectorAll('.scale-control [data-scale]').forEach(b => b.addEventListener('click', () => {
    const k = apply(b.dataset.scale);
    const p = new URLSearchParams(location.search);
    k === '1' ? p.delete('scale') : p.set('scale', k);
    history.replaceState(null, '', p.toString() ? '?' + p : location.pathname);
  }));

  window.dhanjasScale = { apply };
  const start = new URLSearchParams(location.search).get('scale');
  if (start && start !== '1') apply(start);
})();
