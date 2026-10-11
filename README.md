# dhanjas.com

Jain vegetarian recipes for two adults and a toddler — no onion, garlic or root
vegetables — published with GitHub Pages at **https://dhanjas.com**.

- **Front page** (`index.html`): every recipe as a card, filterable by type
  (breakfast, curry, dal…) and tags (night prep, high-protein, Instant Pot,
  paneer…), with search across names and ingredients and sorting by type, A–Z,
  newest or quickest. Filters live in the URL, so `/?cat=dal&tag=Meal%20prep` can
  be bookmarked.
- **Recipe pages** (`recipes/<slug>.html`): the v2 house format, all pages sharing
  one stylesheet, with schema.org Recipe metadata so recipe apps can import them.

## Layout

```
data/recipes/*.json     source of truth, one file per recipe   → docs/RECIPE-FORMAT.md
inbox/                  drop new v2 .html / .json recipes here → docs/INGEST.md
assets/recipe.css       the fixed v2 recipe stylesheet — never edited
assets/site.css         nav bar + front page styles
assets/index.js         front-page filtering
tools/recipes.py        ingest · build · validate · retag · export
index.html, recipes/    generated — don't edit by hand
jhalakbirthday/         unrelated page, left as is
```

## Commands

Python 3.8+, no dependencies.

```sh
python3 tools/recipes.py ingest          # inbox/ → data/recipes/, then build
python3 tools/recipes.py build           # regenerate index.html + recipes/*.html
python3 tools/recipes.py validate        # Jain/toddler/structure checks + density budget
python3 tools/recipes.py retag           # recompute auto-detected tags
python3 tools/recipes.py export <slug>   # standalone v2 HTML in export/
python3 -m unittest discover -s tools    # tests
python3 -m http.server                   # preview at http://localhost:8000
```

The **Recipes** GitHub Action runs ingest + build on every push to `main` that
touches `inbox/`, `data/`, `tools/` or `assets/`, and commits the generated pages.
