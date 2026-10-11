// Batch scaling. The build wraps every number that grows with the batch in
// <data class="q" data-q="1½" data-q2 data-sep data-u data-sp>; times, per-piece
// amounts, sizes and toddler boxes are left unmarked. This multiplies the marked
// values — try any recipe with ?scale=2. format() mirrors tools/dhanjas/quantity.py.
(function () {
  const GLYPHS = { '¼': 1 / 4, '½': 1 / 2, '¾': 3 / 4, '⅓': 1 / 3, '⅔': 2 / 3, '⅛': 1 / 8, '⅜': 3 / 8, '⅝': 5 / 8, '⅞': 7 / 8 };
  const PLURAL = { cup: 'cups', pinch: 'pinches', sprig: 'sprigs', stalk: 'stalks', head: 'heads', inch: 'inches' };
  const SINGULAR = Object.fromEntries(Object.entries(PLURAL).map(([k, v]) => [v, k]));
  const METRIC = ['g', 'ml', 'kg', 'l', 'oz', 'lb'];

  function value(t) {
    t = t.trim();
    if (t.includes(' ') && t.includes('/')) { const [w, f] = t.split(' '); return +w + value(f); }
    if (t.includes('/')) { const [n, d] = t.split('/'); return n / d; }
    const last = t.slice(-1);
    if (last in GLYPHS) return (t.length > 1 ? parseInt(t, 10) : 0) + GLYPHS[last];
    return parseFloat(t);
  }

  function format(v, unit) {
    if ((unit === 'g' || unit === 'ml') && v >= 50) return String(Math.round(v / 5) * 5);
    if (METRIC.includes(unit) && !Number.isInteger(v) && v > 10) return String(Math.round(v));
    let whole = Math.floor(v + 1e-9);
    const frac = v - whole;
    const options = [[0, ''], [1, '']].concat(Object.entries(GLYPHS).map(([g, f]) => [f, g]));
    let best = options[0];
    for (const o of options) if (Math.abs(o[0] - frac) < Math.abs(best[0] - frac) - 1e-9) best = o;
    let glyph = best[1];
    if (best[0] === 1) { whole += 1; glyph = ''; }
    if (!whole) return glyph || '0';
    return whole + glyph;
  }

  function unitFor(unit, v) {
    if (!unit) return '';
    return v > 1 + 1e-9 ? (PLURAL[unit] || unit) : (SINGULAR[unit] || unit);
  }

  const spans = [...document.querySelectorAll('.q[data-q]')];
  spans.forEach(s => { s.dataset.orig = s.textContent; });

  function apply(k) {
    for (const s of spans) {
      if (k === 1) { s.textContent = s.dataset.orig; continue; }
      const d = s.dataset, u = d.u || '';
      const lo = value(d.q) * k, hi = d.q2 ? value(d.q2) * k : null;
      let t = format(lo, u);
      if (hi !== null) t += d.sep + format(hi, u);
      if (u) t += (d.sp || '') + unitFor(u, hi !== null ? hi : lo);
      s.textContent = t;
    }
    document.querySelectorAll('[data-scale]').forEach(b => b.setAttribute('aria-pressed', String(+b.dataset.scale === k)));
    document.documentElement.dataset.scale = k;
  }

  const params = new URLSearchParams(location.search);
  const start = Math.max(0.25, Math.min(10, parseFloat(params.get('scale')) || 1));

  document.querySelectorAll('[data-scale]').forEach(b => b.addEventListener('click', () => {
    const k = +b.dataset.scale;
    apply(k);
    const p = new URLSearchParams(location.search);
    k === 1 ? p.delete('scale') : p.set('scale', k);
    history.replaceState(null, '', p.toString() ? '?' + p : location.pathname);
  }));

  window.dhanjasScale = { apply, format, value };
  if (start !== 1) apply(start);
})();
