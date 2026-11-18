// Batch size: − [1×] + steps through 1× / 1½× / 2× / 3× (the sizes come from the control's
// data-steps). The build computes every amount at each size in Python (tools/dhanjas/portions.py
// — toddler portions stay fixed, "rest" is recomputed) and stores the other sizes on
// <data class="q" data-x1_5 data-x2 data-x3>. This only swaps text. ?scale=1.5 works too.
(function () {
  const control = document.querySelector('.scale-control');
  const STEPS = control ? control.dataset.steps.split(' ') : ['1', '1.5', '2', '3'];
  const LABELS = control ? control.dataset.labels.split('|') : STEPS.map(k => k + '×');
  const value = control && control.querySelector('.scale-value');
  const minus = control && control.querySelector('[data-step="-1"]');
  const plus = control && control.querySelector('[data-step="1"]');
  const marks = [...document.querySelectorAll('data.q')];
  marks.forEach(m => { m.dataset.x1 = m.textContent; });
  const key = k => 'x' + k.replace('.', '_');
  let current = '1';

  function apply(k) {
    k = String(k);
    if (!STEPS.includes(k)) k = '1';
    for (const m of marks) m.textContent = m.dataset[key(k)] || m.dataset.x1;
    const i = STEPS.indexOf(k);
    if (value) { value.textContent = LABELS[i]; value.dataset.scale = k; }
    if (minus) minus.disabled = i === 0;
    if (plus) plus.disabled = i === STEPS.length - 1;
    document.documentElement.dataset.scale = k;
    current = k;
    return k;
  }

  if (control) control.querySelectorAll('[data-step]').forEach(b => b.addEventListener('click', () => {
    const i = Math.min(STEPS.length - 1, Math.max(0, STEPS.indexOf(current) + Number(b.dataset.step)));
    const k = apply(STEPS[i]);
    const p = new URLSearchParams(location.search);
    k === '1' ? p.delete('scale') : p.set('scale', k);
    history.replaceState(null, '', p.toString() ? '?' + p : location.pathname);
  }));

  window.dhanjasScale = { apply };
  const start = new URLSearchParams(location.search).get('scale');
  if (start && start !== '1') apply(start);
})();
