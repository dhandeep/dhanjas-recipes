# dhanjas.com

Jain vegetarian recipes for two adults and a toddler — no onion, garlic or root
vegetables — published with GitHub Pages at **https://dhanjas.com**.

- **Front page** (`index.html`): every recipe as a card, filterable by type
  (breakfast, curry, dal…) and a short fixed tag list (Quick, Night prep, Meal prep,
  High-protein, Instant Pot…), with search across names and ingredients and sorting by type, A–Z,
  newest or quickest. Filters live in the URL, so `/?cat=dal&tag=Meal%20prep` can
  be bookmarked.
- **Recipe pages** (`recipes/<slug>.html`): the v2 house format, all pages sharing
  one stylesheet, with schema.org Recipe metadata so recipe apps can import them.
  Every quantity is batch-scalable — try `?scale=2` on any recipe — and every
  instruction line has a checkbox to tick off while cooking.
- **Data** (`recipes/<slug>.json`, `.jsonld`): each recipe in the house format
  (defined by `schema/recipe.schema.json`) and as schema.org JSON-LD.

## Layout

```
data/recipes/*.json     source of truth, one file per recipe   → docs/RECIPE-FORMAT.md
schema/                 JSON Schema for the recipe format
inbox/                  drop new v2 .html / .json recipes here → docs/INGEST.md
assets/recipe.css       the fixed v2 recipe stylesheet — never edited
assets/site.css         nav bar + front page styles
assets/index.js         front-page filtering
assets/scale.js         batch scaling (?scale=2)
assets/checklist.js     instruction checkboxes
tools/recipes.py        ingest · build · validate · retag · export · scaled
tools/browser-check.mjs renders every page in Chromium and checks it
index.html, recipes/    generated — don't edit by hand
```

## Commands

Python 3.8+, no dependencies.

```sh
python3 tools/recipes.py ingest          # inbox/ → data/recipes/, then build
python3 tools/recipes.py build           # regenerate index.html + recipes/*.html
python3 tools/recipes.py validate        # Jain/toddler/structure checks + density budget
python3 tools/recipes.py retag           # recompute auto-detected tags
python3 tools/recipes.py export <slug>   # standalone v2 HTML in export/ (--format json|jsonld|all)
python3 tools/recipes.py scaled <slug> 2 # preview amounts at 2×
python3 -m unittest discover -s tools    # tests
python3 -m http.server                   # preview at http://localhost:8000

npm install && npm run check:browser     # every page in Chromium: layout, scaling, pixel parity
npm run check:browser -- --shots screenshots   # …and keep the screenshots
```

The **Recipes** GitHub Action runs ingest, build, the tests and the browser check
on every push to `main` that touches recipes or tooling, and commits the generated
pages only if everything passes.
