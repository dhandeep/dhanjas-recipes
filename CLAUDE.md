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

New recipes are **format 3** — follow `docs/RECIPE-SPEC.md` exactly: ingredient ids,
keyed `portions` when an ingredient is used in more than one place (toddler share
included), and every instruction references what it uses as `{@id}` / `{@id:key}`.

1. Save the v2 HTML (or JSON) as `inbox/<category>-<dish>.html`.
2. `python3 tools/recipes.py ingest` — fix any ✗ errors it reports (content
   problems go back to the user; don't silently rewrite their recipe).
   Use `--replace` only when the user confirmed replacing an existing recipe.
3. `python3 -m unittest discover -s tools` and `npm run check:browser` (needs
   `npm install` once), then commit `data/`, `recipes/`, `index.html`,
   `assets/recipes.json`.

Quantities (non-negotiable): every ingredient line has a readable quantity, and every
step line that uses an ingredient says how much. In format 3 that's a reference
(`{@rava:main}`); in older format-2 recipes it's `{¼ tsp}`, `{rest of the 1 cup}`,
`{from Step 1}` or "to taste". `validate` enforces both. `{=…}` marks an amount that
must never scale. When fixing a recipe that fails this, derive amounts from the
recipe's own numbers and tell the user what you changed.
