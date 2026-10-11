"""JSON model -> HTML. Recipe pages reproduce the v2 template markup exactly;
the only additions are a site nav bar and schema.org JSON-LD in <head>."""

import json
from html import escape

from .model import AMT_RE, BOLD_RE, CATEGORIES, plain, protein_grams, times, yield_text
from .portions import lower

SITE = "dhanjas.com"
# stamped on every generated recipe page, so a rebuild can tell its own pages from other HTML at the site root
GENERATOR = '<meta name="generator" content="dhanjas recipes.py">'
EYEBROW = "dhanjas.com · Jain Kitchen"

# The 1× / 2× / 3× batch control in the nav bar. Scaling already works on every
# page via ?scale=2 (assets/scale.js); flip this to show the buttons.
SHOW_SCALE_CONTROL = True
SCALE_STEPS = (1, 2, 3)


def amount_html(text, alts=()):
    """An amount, escaped. When the batch size changes it (alts = the same amount at
    2× and 3×), it's wrapped in <data class="q" data-x2 data-x3> for assets/scale.js
    (<data>, not <span>: recipe.css styles every span inside .recipe-meta)."""
    fixed = text.startswith("=")
    text = text.lstrip("=")
    alts = [a.lstrip("=") for a in alts]
    if fixed or not alts or all(a == text for a in alts):
        return escape(text, quote=False)
    attrs = "".join(' data-x%d="%s"' % (k, escape(a)) for k, a in zip(SCALE_STEPS[1:], alts))
    return '<data class="q"%s>%s</data>' % (attrs, escape(text, quote=False))


def rich(text, alts=()):
    """Inline markup -> HTML. alts: the same text at 2× and 3× (from lower()); each
    {amount} that differs between them becomes scalable."""
    alt_amounts = [AMT_RE.findall(a) for a in alts]
    found = AMT_RE.findall(text)
    if any(len(a) != len(found) for a in alt_amounts):
        alt_amounts = []
    parts, last = [], 0
    for i, m in enumerate(AMT_RE.finditer(text)):
        parts.append(escape(text[last:m.start()], quote=False))
        amount = m.group(1)
        fixed = ' data-fixed' if amount.startswith("=") else ""
        parts.append('<span class="amt"%s>(%s)</span>' % (fixed, amount_html(amount, [a[i] for a in alt_amounts])))
        last = m.end()
    parts.append(escape(text[last:], quote=False))
    return BOLD_RE.sub(lambda m: "<strong>%s</strong>" % m.group(1), "".join(parts))


def e(text):
    return escape(text or "", quote=True)


def _ul(items, indent, alts=()):
    pad = " " * indent
    lines = [pad + "<ul>"]
    for i, item in enumerate(items):
        lines.append("%s  <li>%s</li>" % (pad, rich(item, [a[i] for a in alts])))
    lines.append(pad + "</ul>")
    return lines


def recipe_body(r, alts=()):
    """The <header> + <section class="recipe"> markup, byte-compatible with v2.
    r is a lowered recipe (portions.lower(recipe, 1)); alts are the same recipe
    lowered at 2× and 3× — amounts that differ carry scale markers. No alts (the
    standalone export) means plain v2 markup."""
    L = []
    L.append('<header class="site-header">')
    L.append('  <div class="eyebrow">%s</div>' % e(EYEBROW))
    L.append("  <h1>%s</h1>" % e(r["title"]))
    if r.get("subtitle"):
        L.append('  <p class="subtitle">%s</p>' % e(r["subtitle"]))
    if r.get("badges"):
        L.append('  <div class="badge-row">')
        L += ['    <span class="badge">%s</span>' % e(b) for b in r["badges"]]
        L.append("  </div>")
    L.append("</header>")
    L.append("")
    L.append('<div class="page-shell">')
    L.append("  <main>")
    L.append('  <section class="recipe">')
    L.append('    <div class="recipe-header">')
    if r.get("labels"):
        L.append('      <div class="recipe-eyebrow">%s</div>' % "".join('<span class="recipe-tag">%s</span>' % e(t) for t in r["labels"]))
    L.append('      <h2 class="recipe-name">%s</h2>' % e(r.get("name") or r["title"]))
    if r.get("meta"):
        L.append('      <div class="recipe-meta">')
        for i, m in enumerate(r["meta"]):
            # the whole entry is one element, so it stays a single flex item
            L.append('        <span><span class="dot">◆</span> %s</span>' % amount_html(m, [a["meta"][i] for a in alts]))
        L.append("      </div>")
    L.append("    </div>")

    if r.get("protein") or r.get("nightPrep"):
        L.append('    <div class="strip-row">')
        if r.get("protein"):
            L.append('      <div class="protein-bar">%s</div>' % e(r["protein"]))
        if r.get("nightPrep"):
            L.append('      <div class="night-prep">')
            L.append('        <div class="night-label">🌙 %s</div>' % e(r["nightPrep"]["label"]))
            L += _ul(r["nightPrep"]["items"], 8, [a["nightPrep"]["items"] for a in alts])
            L.append("      </div>")
        L.append("    </div>")

    L.append('    <div class="ingredients-block">')
    L.append('      <div class="section-title">%s</div>' % e(r.get("ingredientsTitle") or "Ingredients"))
    L.append('      <div class="ingredient-groups">')
    for gi, g in enumerate(r["ingredientGroups"]):
        L.append('        <div class="ingredient-group">')
        L.append('          <div class="ingredient-group-label">%s</div>' % e(g["label"]))
        L.append('          <ul class="ingredient-list">')
        for ii, it in enumerate(g["items"]):
            alt = [a["ingredientGroups"][gi]["items"][ii]["amount"] for a in alts]
            L.append('            <li><span class="ing-name">%s</span><span class="ing-amount">%s</span></li>'
                     % (rich(it["name"]), amount_html(it["amount"], alt)))
        L.append("          </ul>")
        L.append("        </div>")
    L.append("      </div>")
    L.append("    </div>")

    L.append('    <div class="steps-block">')
    L.append('      <div class="section-title">%s</div>' % e(r.get("methodTitle") or "Method"))
    n = 0
    for bi, b in enumerate(r["method"]):
        balts = [a["method"][bi] for a in alts]
        if b["type"] == "step":
            n += 1
            L.append('      <div class="step">')
            L.append('        <div class="step-title"><span class="step-num">%d</span> %s</div>' % (n, e(b["title"])))
            L += _ul(b["items"], 8, [x["items"] for x in balts])
            L.append("      </div>")
        elif b["type"] == "toddler":
            L.append('      <div class="toddler-box">')
            L.append('        <div class="toddler-label">👶 %s</div>' % e(b["label"]))
            L += _ul(b["items"], 8)  # her portion doesn't grow with the batch
            L.append("      </div>")
        elif b["type"] == "tip":
            L.append('      <div class="tip-box"><strong>%s</strong> %s</div>' % (e(b.get("label") or "Tip"), rich(b["text"])))
    L.append("    </div>")
    L.append("  </section>")
    L.append("  </main>")
    L.append("</div>")
    return "\n".join(L)


TO_TOP = """<button class="to-top" aria-label="Back to top">↑</button>

<script>
  const btn = document.querySelector('.to-top');
  addEventListener('scroll', () => btn.classList.toggle('show', scrollY > 600), { passive: true });
  btn.addEventListener('click', () => scrollTo({ top: 0, behavior: 'smooth' }));
</script>"""


def iso_minutes(m):
    h, mm = divmod(m, 60)
    return "PT" + ("%dH" % h if h else "") + ("%dM" % mm if mm or not h else "")


def json_ld(r):
    return json.dumps(json_ld_data(r), ensure_ascii=False, indent=2).replace("</", "<\\/")


def json_ld_data(recipe):
    """schema.org/Recipe — the format Google, Paprika, Mealie, etc. understand."""
    r = lower(recipe, 1)
    data = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": r["title"],
        "description": r.get("subtitle", ""),
        "author": {"@type": "Organization", "name": SITE},
        "recipeCategory": CATEGORIES.get(r["category"], r["category"]),
        "recipeCuisine": "Indian (Jain)",
        "suitableForDiet": "https://schema.org/VegetarianDiet",
        "keywords": ", ".join(r.get("labels", []) + r.get("tags", []) + r.get("badges", [])),
        "recipeIngredient": [],
        "recipeInstructions": [],
    }
    if r.get("added"):
        data["datePublished"] = r["added"]
    y = yield_text(r)
    if y:
        data["recipeYield"] = y
    t = times(r)
    for key, prop in (("prep", "prepTime"), ("cook", "cookTime"), ("total", "totalTime")):
        if key in t:
            data[prop] = iso_minutes(t[key])
    g = protein_grams(r)
    if g:
        data["nutrition"] = {"@type": "NutritionInformation", "proteinContent": "%s g" % g, "description": r["protein"]}

    for grp in r["ingredientGroups"]:
        for it in grp["items"]:
            name, amt = plain(it["name"]), it["amount"]
            data["recipeIngredient"].append("%s, %s" % (name, amt) if amt.lower().startswith(("to taste", "as needed", "for")) else "%s %s" % (amt, name))

    if r.get("nightPrep"):
        data["recipeInstructions"].append({
            "@type": "HowToSection", "name": r["nightPrep"]["label"],
            "itemListElement": [{"@type": "HowToStep", "text": plain(i)} for i in r["nightPrep"]["items"]],
        })
    section = None
    for b in r["method"]:
        if b["type"] in ("step", "toddler"):
            name = b["title"] if b["type"] == "step" else "👶 " + b["label"]
            section = {"@type": "HowToSection", "name": name,
                       "itemListElement": [{"@type": "HowToStep", "text": plain(i)} for i in b["items"]]}
            data["recipeInstructions"].append(section)
        elif b["type"] == "tip":
            tip = {"@type": "HowToTip", "text": plain(b["text"])}
            if section:
                section["itemListElement"].append(tip)
            else:
                data["recipeInstructions"].append(tip)
    return data


def scale_control():
    buttons = "".join('<button type="button" data-scale="%d" aria-pressed="%s">%d×</button>'
                      % (n, "true" if n == 1 else "false", n) for n in SCALE_STEPS)
    return '  <div class="scale-control" role="group" aria-label="Batch size">%s</div>' % buttons


def recipe_page(recipe, css, standalone=False):
    """Full recipe page from a recipe in either format. `css` is the v2 stylesheet
    text (inlined when standalone, which also drops the site nav, scale markers and
    JSON-LD — a plain v2 file)."""
    r = lower(recipe, 1)
    alts = () if standalone else [lower(recipe, k) for k in SCALE_STEPS[1:]]
    head = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        "<title>%s — %s</title>" % (e(r["title"]), SITE),
    ]
    if standalone:
        head += ["<style>", css.rstrip("\n"), "</style>"]
    else:
        slug = e(r["slug"])
        head += [
            GENERATOR,
            '<meta name="description" content="%s">' % e(r.get("subtitle", "")),
            '<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">',
            '<link rel="stylesheet" href="assets/recipe.css">',
            '<link rel="stylesheet" href="assets/site.css">',
            '<link rel="alternate" type="application/json" href="recipes/%s.json" title="Recipe data (dhanjas format)">' % slug,
            '<link rel="alternate" type="application/ld+json" href="recipes/%s.jsonld" title="Recipe data (schema.org)">' % slug,
            '<script type="application/ld+json">',
            json_ld(r),
            "</script>",
            '<script src="assets/scale.js" defer></script>',
            '<script src="assets/checklist.js" defer></script>',
        ]
    head += ["</head>", "<body>", ""]
    nav = []
    if not standalone:
        cat = CATEGORIES.get(r["category"], r["category"])
        nav = ['<nav class="site-nav" aria-label="Site">',
               '  <a class="site-nav-home" href="./">← All recipes</a>']
        if SHOW_SCALE_CONTROL:
            nav.append(scale_control())
        nav += ['  <a class="site-nav-cat" href="./?cat=%s">%s</a>' % (e(r["category"]), e(cat)), "</nav>", ""]
    return "\n".join(head + nav + [recipe_body(r, alts), "", TO_TOP, "</body>", "</html>", ""])
