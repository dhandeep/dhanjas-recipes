# dhanjas.com recipe site

Static GitHub Pages site. Recipes live as JSON in `data/recipes/`; `tools/recipes.py`
generates `index.html` and `recipes/*.html`. Read `docs/RECIPE-FORMAT.md` before
touching recipe data and `docs/INGEST.md` for the publishing flow.

## Rules

- Never hand-edit `index.html`, `recipes/*.html` or `assets/recipes.json` — edit the
  JSON (or tools) and run `python3 tools/recipes.py build`.
- `assets/recipe.css` is the fixed v2 stylesheet from the recipe spec. Never change
  it. Site-only styling goes in `assets/site.css`.
- Household rules the validator enforces: strict Jain vegetarian (no onion, garlic,
  eggs, meat, fish; no root vegetables for adults — carrot/potato only in the
  toddler's portion; dairy and ginger are fine). Toddler boxes sit in the method at
  the moment her portion is pulled, before chili goes in.

## Adding a recipe

1. Save the v2 HTML (or JSON) as `inbox/<category>-<dish>.html`.
2. `python3 tools/recipes.py ingest` — fix any ✗ errors it reports (content
   problems go back to the user; don't silently rewrite their recipe).
   Use `--replace` only when the user confirmed replacing an existing recipe.
3. `python3 -m unittest discover -s tools` and `npm run check:browser` (needs
   `npm install` once), then commit `data/`, `recipes/`, `index.html`,
   `assets/recipes.json`.

Quantities: every ingredient amount and every step `{amount}` must lead with a
number the scaler can read; `{=…}` marks an amount that must never scale.
