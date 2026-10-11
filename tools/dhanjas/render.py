"""JSON model -> HTML. Recipe pages reproduce the v2 template markup exactly;
the only additions are a site nav bar and schema.org JSON-LD in <head>."""

import json
from html import escape

from .model import AMT_RE, BOLD_RE, CATEGORIES, plain, protein_grams, times, yield_text

SITE = "dhanjas.com"
EYEBROW = "dhanjas.com · Jain Kitchen"


def rich(text):
    """Inline markup -> HTML."""
    out = escape(text, quote=False)
    out = AMT_RE.sub(lambda m: '<span class="amt">(%s)</span>' % m.group(1), out)
    return BOLD_RE.sub(lambda m: "<strong>%s</strong>" % m.group(1), out)


def e(text):
    return escape(text or "", quote=True)


def _ul(items, indent):
    pad = " " * indent
    lines = [pad + "<ul>"]
    lines += ["%s  <li>%s</li>" % (pad, rich(i)) for i in items]
    lines.append(pad + "</ul>")
    return lines


def recipe_body(r):
    """The <header> + <section class="recipe"> markup, byte-compatible with v2."""
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
        L += ['        <span><span class="dot">◆</span> %s</span>' % e(m) for m in r["meta"]]
        L.append("      </div>")
    L.append("    </div>")

    if r.get("protein") or r.get("nightPrep"):
        L.append('    <div class="strip-row">')
        if r.get("protein"):
            L.append('      <div class="protein-bar">%s</div>' % e(r["protein"]))
        if r.get("nightPrep"):
            L.append('      <div class="night-prep">')
            L.append('        <div class="night-label">🌙 %s</div>' % e(r["nightPrep"]["label"]))
            L += _ul(r["nightPrep"]["items"], 8)
            L.append("      </div>")
        L.append("    </div>")

    L.append('    <div class="ingredients-block">')
    L.append('      <div class="section-title">%s</div>' % e(r.get("ingredientsTitle") or "Ingredients"))
    L.append('      <div class="ingredient-groups">')
    for g in r["ingredientGroups"]:
        L.append('        <div class="ingredient-group">')
        L.append('          <div class="ingredient-group-label">%s</div>' % e(g["label"]))
        L.append('          <ul class="ingredient-list">')
        for it in g["items"]:
            L.append('            <li><span class="ing-name">%s</span><span class="ing-amount">%s</span></li>'
                     % (rich(it["name"]), e(it["amount"])))
        L.append("          </ul>")
        L.append("        </div>")
    L.append("      </div>")
    L.append("    </div>")

    L.append('    <div class="steps-block">')
    L.append('      <div class="section-title">%s</div>' % e(r.get("methodTitle") or "Method"))
    n = 0
    for b in r["method"]:
        if b["type"] == "step":
            n += 1
            L.append('      <div class="step">')
            L.append('        <div class="step-title"><span class="step-num">%d</span> %s</div>' % (n, e(b["title"])))
            L += _ul(b["items"], 8)
            L.append("      </div>")
        elif b["type"] == "toddler":
            L.append('      <div class="toddler-box">')
            L.append('        <div class="toddler-label">👶 %s</div>' % e(b["label"]))
            L += _ul(b["items"], 8)
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
    """schema.org/Recipe — the format Google, Paprika, Mealie, etc. understand."""
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
    return json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")


def recipe_page(r, css, standalone=False):
    """Full recipe page. `css` is the v2 stylesheet text (inlined when standalone)."""
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
        head += [
            '<meta name="description" content="%s">' % e(r.get("subtitle", "")),
            '<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">',
            '<link rel="stylesheet" href="../assets/recipe.css">',
            '<link rel="stylesheet" href="../assets/site.css">',
            '<script type="application/ld+json">',
            json_ld(r),
            "</script>",
        ]
    head += ["</head>", "<body>", ""]
    nav = []
    if not standalone:
        cat = CATEGORIES.get(r["category"], r["category"])
        nav = [
            '<nav class="site-nav" aria-label="Site">',
            '  <a class="site-nav-home" href="../">← All recipes</a>',
            '  <a class="site-nav-cat" href="../?cat=%s">%s</a>' % (e(r["category"]), e(cat)),
            "</nav>",
            "",
        ]
    return "\n".join(head + nav + [recipe_body(r), "", TO_TOP, "</body>", "</html>", ""])
