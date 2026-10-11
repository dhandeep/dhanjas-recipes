# Adding recipes

The recipe prompt keeps doing what it does — producing a v2 HTML file that has
passed `dhanjas-recipe-validator` — and the file goes into this repo's `inbox/`
instead of (or as well as) Google Drive. Pick whichever route is handiest:

| Route | How |
|---|---|
| **GitHub web / mobile app** | Open `inbox/` on github.com → *Add file → Upload files* → drop the `.html` → *Commit to main*. The **Recipes** Action ingests it and the site updates a minute later. |
| **Claude with the GitHub connector** | Ask Claude to commit the generated file to `inbox/<slug>.html` on `main` in `dhandeep/dhanjas-recipes`. |
| **Claude Code in this repo** | "Add this recipe" — it writes the file to `inbox/` and runs `python3 tools/recipes.py ingest` (see `CLAUDE.md`). |
| **Local** | Copy the file into `inbox/`, run `python3 tools/recipes.py ingest`, commit and push. |

`ingest` parses the HTML, runs the checks below, writes `data/recipes/<slug>.json`,
rebuilds every page and deletes the inbox file. If a check fails the file stays in
`inbox/` and nothing is published.

- **Errors (block publishing):** anything that breaks `schema/recipe.schema.json`
  (bad slug prefix, missing title or subtitle, unknown fields, empty steps),
  ingredient amounts with no quantity the 1×/2× control can read (write `1 tsp`,
  `2–3`, `200g`, or `to taste` / `a pinch` / `as needed` / `optional`), step lines
  that use an ingredient without its quantity (write `{¼ tsp}`,
  `{rest of the 1 cup}`, `{from Step 1}` — see RECIPE-FORMAT.md),
  onion/garlic/eggs/meat anywhere in the dish, root vegetables outside a toddler
  portion.
- **Warnings (printed, don't block):** density budget (3–5 groups of 4–8 lines,
  2–4 steps of 4–8 bullets, 1 tip), chili going in before the first toddler box,
  honey/mushroom/yeast for a second look, and
  restricted words inside tips.

After the build, the workflow renders every page in Chromium
(`tools/browser-check.mjs`): desktop and phone widths, no sideways scrolling, every
ingredient line showing an amount, 2× scaling matching the Python reference, the
instruction checkboxes working, and each page pixel-identical to the standalone v2 file. Nothing is committed unless
that passes, and the screenshots are kept on the workflow run for 14 days.

These checks are a backstop. They don't replace the full `dhanjas-recipe-validator`
skill, which also judges cooking logic.

### Updating a recipe

Edit `data/recipes/<slug>.json` directly and push; the Action rebuilds. Or drop a
corrected `.html` into `inbox/` and run `ingest --replace` (the Action does not
replace existing recipes on its own, so it can't overwrite one by accident — run
it locally or ask Claude to).

### Getting a standalone file back

`python3 tools/recipes.py export <slug>` writes `export/<slug>.html`: a
self-contained v2 file with the stylesheet inlined, identical in structure to what
the prompt produces. Use it for sharing a single file or keeping Drive in sync.
`--format json` / `jsonld` / `all` gives the house JSON or schema.org versions.

## Suggested prompt change

New recipes should be written in **format 3** (`docs/RECIPE-SPEC.md`) and submitted as
JSON. Section 8 of the spec has a drop-in replacement for the **Recipe Output Format**
section of the recipe prompt; copy `RECIPE-SPEC.md` into the Claude project next to
the prompt so it can be read before each recipe.

Then replace the **Saving to Google Drive** section with:

> ## Publishing to dhanjas.com
>
> After the recipe passes validation, commit the JSON file to the GitHub repo
> `dhandeep/dhanjas-recipes` on branch `main` at `inbox/<category>-<dish>.json`.
> A GitHub Action validates it, builds the page and publishes it at
> `https://dhanjas.com/recipes/<category>-<dish>.html` within a couple of minutes.
>
> Before committing, check `data/recipes/<category>-<dish>.json` doesn't already
> exist. If it does, ask whether this replaces the existing recipe — the Action
> refuses to overwrite one.

v2 HTML files (the older format) still ingest, but can't carry portions — use them
only for recipes written before format 3.
