# Adding recipes

Each recipe is written offline, one at a time, by Claude using the recipe prompt
([`RECIPE-PROMPT.md`](RECIPE-PROMPT.md)). The prompt produces one **format-3 JSON file**
([`RECIPE-SPEC.md`](RECIPE-SPEC.md)), and that file goes into this repo's `inbox/`.
Use whichever route is handiest:

| Route | How |
|---|---|
| **GitHub web / mobile app** | Open `inbox/` on github.com → *Add file → Upload files* → drop the `.json` → *Commit to main*. The **Recipes** Action ingests it and the site updates a minute later. |
| **Claude with the GitHub connector** | Ask Claude to commit the generated file to `inbox/<slug>.json` on `main` in `dhandeep/dhanjas-recipes`. |
| **Claude Code in this repo** | "Add this recipe" — it writes the file to `inbox/` and runs `python3 tools/recipes.py ingest` (see `CLAUDE.md`). |
| **Local** | Copy the file into `inbox/`, run `python3 tools/recipes.py ingest`, commit and push. |

`ingest` reads the JSON (or an older v2 `.html`), runs the checks below, writes `data/recipes/<slug>.json`,
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

These checks are a backstop. They don't replace the `dhanjas-recipe-validator`
skill ([`.claude/skills/dhanjas-recipe-validator/SKILL.md`](../.claude/skills/dhanjas-recipe-validator/SKILL.md)),
which also judges cooking logic: toddler timing with spice blends and pepper,
set-aside items coming back, portions that make sense, scaling at 2×. Claude Code
uses it from the repo automatically; upload the same file as a skill in Claude chat.

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

## The recipe prompt

[`RECIPE-PROMPT.md`](RECIPE-PROMPT.md) is the full prompt for the Claude project that
writes recipes. Paste it into the project instructions and add `RECIPE-SPEC.md` and
`data/recipes/rava-upma.json` as project files. It replaces the v2-HTML
and Google Drive sections of the old prompt.

v2 HTML files (the older format) still ingest, but can't carry portions — use them
only for recipes written before format 3.
