// Renders the built site in Chromium and checks what a reader would see.
//
//   npm install && npm run check:browser            (after `python3 tools/recipes.py build`)
//   node tools/browser-check.mjs --shots screenshots  keep every screenshot for review
//
// Per recipe page, at desktop (1280px) and phone (390px) widths:
//   · no JS errors, stylesheets applied, nothing wider than the screen
//   · every ingredient line shows an amount
//   · pixel parity: the page (shared recipe.css) renders identically to the
//     standalone v2 file (stylesheet inlined) that `recipes.py export` writes
//   · ?scale=2 — every scalable number matches `recipes.py scaled` (Python is the
//     reference), toddler boxes untouched; ?scale=1 changes nothing
// Front page: one card per recipe, every Type/Tag filter count matches the data.
//
// Exits non-zero on any failure. Set CHROMIUM_PATH to use a specific browser.

import { chromium } from 'playwright';
import pixelmatch from 'pixelmatch';
import { PNG } from 'pngjs';
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { readFileSync, existsSync, mkdirSync, readdirSync, writeFileSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname;
const shotsArg = process.argv.indexOf('--shots');
const SHOTS = shotsArg > -1 ? process.argv[shotsArg + 1] || 'screenshots' : null;
if (SHOTS) mkdirSync(join(ROOT, SHOTS), { recursive: true });

const failures = [];
const fail = (where, msg) => { failures.push(`${where}: ${msg}`); console.log(`  ✗ ${where}: ${msg}`); };

// ---- build the standalone exports to compare against ----
execFileSync('python3', [join(ROOT, 'tools/recipes.py'), 'export', '--all', '--format', 'html'], { cwd: ROOT, stdio: 'ignore' });
const slugs = readdirSync(join(ROOT, 'data/recipes')).filter(f => f.endsWith('.json')).map(f => f.slice(0, -5)).sort();
const recipes = Object.fromEntries(slugs.map(s => [s, JSON.parse(readFileSync(join(ROOT, 'data/recipes', s + '.json'), 'utf8'))]));

// ---- static server for the repo root ----
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml' };
const server = createServer((req, res) => {
  let path = normalize(decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (path.endsWith('/')) path += 'index.html';
  const file = join(ROOT, path);
  if (!file.startsWith(ROOT) || !existsSync(file)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': TYPES[extname(file)] || 'application/octet-stream' });
  res.end(readFileSync(file));
}).listen(0);
const BASE = `http://127.0.0.1:${server.address().port}`;

const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const VIEWPORTS = { desktop: { width: 1280, height: 900 }, phone: { width: 390, height: 844 } };

async function page(viewport, errors) {
  const p = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  p.on('pageerror', e => errors.push(String(e)));
  p.on('console', m => m.type() === 'error' && errors.push(m.text()));
  return p;
}

// Screenshot of the recipe itself (the site nav is hidden by the caller so the
// two renderings are comparable).
async function recipeShot(p) {
  await p.evaluate(() => document.fonts && document.fonts.ready);
  return PNG.sync.read(await p.screenshot({ fullPage: true, animations: 'disabled' }));
}

for (const slug of slugs) {
  console.log(slug);
  const r = recipes[slug];
  for (const [vpName, viewport] of Object.entries(VIEWPORTS)) {
    const where = `${slug} @${vpName}`;
    const errors = [];
    const p = await page(viewport, errors);
    const resp = await p.goto(`${BASE}/recipes/${slug}.html`);
    if (!resp.ok()) { fail(where, `HTTP ${resp.status()}`); continue; }

    const info = await p.evaluate(() => ({
      overflow: document.documentElement.scrollWidth - innerWidth,
      headerBg: getComputedStyle(document.querySelector('.site-header')).backgroundColor,
      navBg: getComputedStyle(document.querySelector('.site-nav')).backgroundColor,
      missingAmounts: [...document.querySelectorAll('.ingredient-list li')]
        .filter(li => !li.querySelector('.ing-amount')?.textContent.trim()).map(li => li.textContent.trim()),
      toddlerBoxes: document.querySelectorAll('.toddler-box').length,
      jsonld: !!document.querySelector('script[type="application/ld+json"]'),
    }));
    if (info.overflow > 0) fail(where, `page is ${info.overflow}px wider than the screen`);
    if (info.headerBg !== 'rgb(45, 80, 22)') fail(where, `recipe.css not applied (header ${info.headerBg})`);
    if (info.navBg !== 'rgb(45, 80, 22)') fail(where, `site.css not applied (nav ${info.navBg})`);
    if (info.missingAmounts.length) fail(where, `ingredient lines without an amount: ${info.missingAmounts.join(' | ')}`);
    const wantToddler = r.method.filter(b => b.type === 'toddler').length;
    if (info.toddlerBoxes !== wantToddler) fail(where, `${info.toddlerBoxes} toddler boxes, data has ${wantToddler}`);
    if (!info.jsonld) fail(where, 'no schema.org JSON-LD');

    // Parity with the standalone v2 file (stylesheet inlined, no scale markers):
    //  1. layout — with the markers in place, every block sits exactly where it
    //     does in the v2 file (the markers must not move anything);
    //  2. pixels — with the markers unwrapped, the two renderings are identical.
    //     (Unwrapped because an inline element boundary can nudge kerning by a
    //     sub-pixel, which is invisible but not pixel-identical.)
    const sp = await page(viewport, errors);
    await sp.goto(`${BASE}/export/${slug}.html`);
    await sp.addStyleTag({ content: '.site-nav{display:none!important}' });
    await p.addStyleTag({ content: '.site-nav{display:none!important}' });
    const boxes = pg => pg.evaluate(() => [...document.querySelectorAll(
      '.site-header, .recipe-header, .recipe-meta > span, .strip-row > *, .ingredient-group, .ingredient-list li, .step, .step li, .toddler-box, .tip-box')]
      .map(el => { const b = el.getBoundingClientRect(); return [el.className || el.tagName, Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)].join(' '); }));
    const [siteBoxes, v2Boxes] = [await boxes(p), await boxes(sp)];
    const moved = siteBoxes.findIndex((b, i) => b !== v2Boxes[i]);
    if (siteBoxes.length !== v2Boxes.length || moved > -1) {
      fail(where, `layout differs from the standalone v2 file at ${siteBoxes[moved]} vs ${v2Boxes[moved]}`);
    }
    const unwrap = pg => pg.evaluate(() => { document.querySelectorAll('data.q').forEach(d => d.replaceWith(d.textContent)); document.body.normalize(); });
    await unwrap(p);
    const site = await recipeShot(p);
    if (SHOTS) writeFileSync(join(ROOT, SHOTS, `${slug}.${vpName}.png`), PNG.sync.write(site));
    const standalone = await recipeShot(sp);
    if (site.width !== standalone.width || site.height !== standalone.height) {
      fail(where, `differs from the standalone v2 file (${site.width}×${site.height} vs ${standalone.width}×${standalone.height})`);
    } else {
      const diff = new PNG({ width: site.width, height: site.height });
      const n = pixelmatch(site.data, standalone.data, diff.data, site.width, site.height, { threshold: 0.1 });
      if (n > 0) {
        fail(where, `${n} pixels differ from the standalone v2 file`);
        if (SHOTS) writeFileSync(join(ROOT, SHOTS, `${slug}.${vpName}.diff.png`), PNG.sync.write(diff));
      }
    }
    await sp.close();

    if (vpName === 'desktop') {
      // scaling: browser (assets/scale.js) vs Python reference
      await p.goto(`${BASE}/recipes/${slug}.html`);
      const want = JSON.parse(execFileSync('python3', [join(ROOT, 'tools/recipes.py'), 'scaled', slug, '2'], { cwd: ROOT }).toString());
      const before = await p.evaluate(() => [...document.querySelectorAll('data.q')].map(s => s.textContent));
      const toddlerBefore = await p.evaluate(() => [...document.querySelectorAll('.toddler-box')].map(b => b.textContent));
      const got = await p.evaluate(() => { window.dhanjasScale.apply(2); return [...document.querySelectorAll('data.q')].map(s => s.textContent); });
      if (got.length !== want.length) fail(where, `scale: ${got.length} scalable amounts on the page, Python found ${want.length}`);
      want.forEach((w, i) => {
        if (before[i] !== w.original) fail(where, `scale: amount ${i} reads ${JSON.stringify(before[i])}, expected ${JSON.stringify(w.original)}`);
        if (got[i] !== w.scaled) fail(where, `scale 2×: ${JSON.stringify(w.original)} → ${JSON.stringify(got[i])}, Python says ${JSON.stringify(w.scaled)}`);
      });
      const toddlerAfter = await p.evaluate(() => [...document.querySelectorAll('.toddler-box')].map(b => b.textContent));
      if (JSON.stringify(toddlerAfter) !== JSON.stringify(toddlerBefore)) fail(where, 'scale: a toddler box changed');
      if (SHOTS) await p.screenshot({ path: join(ROOT, SHOTS, `${slug}.scale2.png`), fullPage: true });
      const back = await p.evaluate(() => { window.dhanjasScale.apply(1); return [...document.querySelectorAll('data.q')].map(s => s.textContent); });
      if (JSON.stringify(back) !== JSON.stringify(before)) fail(where, 'scale: 1× does not restore the original amounts');
    }
    if (errors.length) fail(where, `browser errors: ${errors.join(' | ')}`);
    await p.close();
  }
}

// ---- front page ----
console.log('index');
for (const [vpName, viewport] of Object.entries(VIEWPORTS)) {
  const where = `index @${vpName}`;
  const errors = [];
  const p = await page(viewport, errors);
  await p.goto(`${BASE}/`);
  const cards = await p.locator('.card').count();
  if (cards !== slugs.length) fail(where, `${cards} cards for ${slugs.length} recipes`);
  const overflow = await p.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  if (overflow > 0) fail(where, `page is ${overflow}px wider than the screen`);
  if (SHOTS) await p.screenshot({ path: join(ROOT, SHOTS, `index.${vpName}.png`), fullPage: true });

  if (vpName === 'desktop') {
    const all = Object.values(recipes);
    for (const cat of await p.locator('[data-cat]').evaluateAll(bs => bs.map(b => b.dataset.cat))) {
      await p.click(`[data-cat="${cat}"]`);
      const shown = await p.locator('.card:not([hidden])').count();
      const want = cat ? all.filter(r => r.category === cat).length : all.length;
      if (shown !== want) fail(where, `Type "${cat || 'All'}" shows ${shown}, data has ${want}`);
    }
    await p.click('[data-cat=""]');
    const tags = await p.locator('[data-tag]').evaluateAll(bs => bs.map(b => b.dataset.tag));
    if (tags.length > 8) fail(where, `${tags.length} tag filters — the list should stay short`);
    for (const tag of tags) {
      await p.click(`[data-tag="${tag}"]`);
      const shown = await p.locator('.card:not([hidden])').count();
      const want = all.filter(r => (r.tags || []).includes(tag)).length;
      if (shown !== want) fail(where, `Tag "${tag}" shows ${shown}, data has ${want}`);
      await p.click(`[data-tag="${tag}"]`);
    }
    await p.locator('.card a').first().click();
    await p.waitForLoadState();
    if (!/\/recipes\/.+\.html$/.test(p.url())) fail(where, `card link went to ${p.url()}`);
  }
  if (errors.length) fail(where, `browser errors: ${errors.join(' | ')}`);
  await p.close();
}

await browser.close();
server.close();
console.log(failures.length ? `\n${failures.length} problem(s)` : `\nAll checks passed: ${slugs.length} recipes × 2 viewports + front page`);
process.exit(failures.length ? 1 : 0);
