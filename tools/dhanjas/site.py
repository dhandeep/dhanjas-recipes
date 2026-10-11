"""Front page + search index."""

import json
from collections import Counter

from .model import CATEGORIES, TAGS, TAG_NAMES, all_text, plain, times
from .render import EYEBROW, SITE, e


def card_data(r):
    t = times(r)
    return {
        "slug": r["slug"],
        "title": r["title"],
        "subtitle": r.get("subtitle", ""),
        "category": r["category"],
        "categoryName": CATEGORIES.get(r["category"], r["category"]),
        "tags": [t for t in TAG_NAMES if t in r.get("tags", [])],
        "protein": r.get("protein") or "",
        "minutes": t.get("total"),
        "added": r.get("added", ""),
        "ingredients": [plain(i["name"]) for g in r["ingredientGroups"] for i in g["items"]],
        "url": r["slug"],  # GitHub Pages serves <slug>.html at /<slug>
    }


def sort_key(r):
    order = list(CATEGORIES)
    return (order.index(r["category"]) if r["category"] in order else 99, r["title"].lower())


def card_html(c):
    chips = "".join('<span class="chip">%s</span>' % e(t) for t in c["tags"])
    time = '<span>⏱ %d min</span>' % c["minutes"] if c["minutes"] else ""
    return (
        '<li class="card" data-slug="%(slug)s">'
        '<a href="%(url)s">'
        '<span class="card-cat">%(cat)s</span>'
        '<span class="card-title">%(title)s</span>'
        '<span class="card-sub">%(sub)s</span>'
        '<span class="card-protein">%(protein)s</span>'
        '<span class="card-chips">%(chips)s</span>'
        '<span class="card-foot">%(time)s</span>'
        "</a></li>"
    ) % {
        "slug": e(c["slug"]), "url": e(c["url"]), "cat": e(c["categoryName"]), "title": e(c["title"]),
        "sub": e(c["subtitle"]), "protein": e(c["protein"]), "chips": chips, "time": time,
    }


def index_page(recipes):
    recipes = sorted(recipes, key=sort_key)
    cards = [card_data(r) for r in recipes]
    cat_counts = Counter(r["category"] for r in recipes)
    tag_counts = Counter(t for c in cards for t in c["tags"])

    cat_buttons = ['<button type="button" class="pill" data-cat="" aria-pressed="true">All <span class="n">%d</span></button>' % len(recipes)]
    cat_buttons += [
        '<button type="button" class="pill" data-cat="%s" aria-pressed="false">%s <span class="n">%d</span></button>' % (k, e(v), cat_counts[k])
        for k, v in CATEGORIES.items() if cat_counts[k]
    ]
    # Fixed vocabulary, in a fixed order; a tag that matches nothing (or everything) filters nothing.
    tag_buttons = [
        '<button type="button" class="pill pill-tag" data-tag="%s" title="%s" aria-pressed="false">%s <span class="n">%d</span></button>'
        % (e(t), e(desc), e(t), tag_counts[t])
        for t, desc in TAGS if 0 < tag_counts[t] < len(recipes)
    ]

    data = json.dumps(cards, ensure_ascii=False).replace("</", "<\\/")
    return "\n".join([
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        "<title>Jain Kitchen — %s</title>" % SITE,
        '<meta name="description" content="Jain vegetarian recipes for a family of two adults and a toddler — no onion, no garlic, no root vegetables.">',
        '<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">',
        '<link rel="stylesheet" href="assets/recipe.css">',
        '<link rel="stylesheet" href="assets/site.css">',
        "</head>",
        '<body class="home">',
        "",
        '<header class="site-header">',
        '  <div class="eyebrow">%s</div>' % e(EYEBROW),
        "  <h1>Recipes</h1>",
        '  <p class="subtitle">Strict Jain vegetarian · no onion, garlic or root veg</p>',
        "</header>",
        "",
        '<div class="page-shell">',
        "  <main>",
        '  <section class="finder" aria-label="Find a recipe">',
        '    <label class="search"><span class="visually-hidden">Search recipes</span>',
        '      <input id="q" type="search" placeholder="Search recipes or ingredients — paneer, moong, Instant Pot…" autocomplete="off">',
        "    </label>",
        '    <div class="section-title">Type</div>',
        '    <div class="pill-row" id="cats">%s</div>' % "".join(cat_buttons),
        '    <div class="section-title">Tags</div>',
        '    <div class="pill-row" id="tags">%s</div>' % "".join(tag_buttons),
        '    <div class="finder-foot"><span id="count">%d recipes</span>' % len(recipes),
        '      <label class="sort">Sort <select id="sort"><option value="type">By type</option><option value="az">A–Z</option><option value="new">Newest</option><option value="quick">Quickest</option></select></label>',
        '      <button type="button" id="clear" class="link-btn" hidden>Clear filters</button></div>',
        "  </section>",
        '  <ul class="cards" id="cards">',
        "\n".join("    " + card_html(c) for c in cards),
        "  </ul>",
        '  <p class="empty" id="empty" hidden>No recipes match. <button type="button" class="link-btn" data-clear>Clear filters</button></p>',
        "  </main>",
        "</div>",
        "",
        '<script id="recipe-data" type="application/json">%s</script>' % data,
        '<script src="assets/index.js"></script>',
        "</body>",
        "</html>",
        "",
    ])


def search_index(recipes):
    """assets/recipes.json — every recipe's card data plus full text, for other tools."""
    out = []
    for r in sorted(recipes, key=sort_key):
        c = card_data(r)
        c["text"] = all_text(r)
        out.append(c)
    return json.dumps(out, ensure_ascii=False, indent=1) + "\n"
