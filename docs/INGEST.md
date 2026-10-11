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
  `2–3`, `200g`, or `to taste` / `a pinch` / `as needed` / `optional`),
  onion/garlic/eggs/meat anywhere in the dish, root vegetables outside a toddler
  portion.
- **Warnings (printed, don't block):** density budget (3–5 groups of 4–8 lines,
  2–4 steps of 4–8 bullets, 1 tip), chili going in before the first toddler box,
  "add …" bullets with no `{amount}`, honey/mushroom/yeast for a second look, and
  restricted words inside tips.

After the build, the workflow renders every page in Chromium
(`tools/browser-check.mjs`): desktop and phone widths, no sideways scrolling, every
ingredient line showing an amount, 2× scaling matching the Python reference, and
each page pixel-identical to the standalone v2 file. Nothing is committed unless
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

Replace the **Saving to Google Drive** section of the recipe prompt with this
(keep the Drive part if you still want copies there):

> ## Publishing to dhanjas.com
>
> After the recipe passes `dhanjas-recipe-validator`, commit the HTML file to the
> GitHub repo `dhandeep/dhanjas-recipes` on branch `main` at `inbox/<category>-<dish>.html`.
> A GitHub Action converts it, rebuilds the site and publishes it at
> `https://dhanjas.com/recipes/<category>-<dish>.html` within a couple of minutes.
>
> Before committing, check `data/recipes/<category>-<dish>.json` doesn't already
> exist. If it does, ask whether this replaces the existing recipe — the Action
> refuses to overwrite one.
>
> The site regenerates the page from the recipe's content, so the stylesheet in
> the file doesn't matter to it — but keep following `RECIPE-HTML-SPEC.md` exactly,
> because the class names are how the content is read.

If you use Claude in a project without the GitHub connector, the GitHub
web-upload route above is the fallback: download the file and upload it to `inbox/`.
