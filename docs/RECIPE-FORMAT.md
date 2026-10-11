# Recipe format

Every recipe is one JSON file in `data/recipes/<slug>.json`. It is the source of
truth: the recipe page, the front-page card, the search index and the
schema.org metadata are all generated from it.

The format is formally defined by **[`schema/recipe.schema.json`](../schema/recipe.schema.json)**
(JSON Schema 2020-12, published at `https://dhanjas.com/schema/recipe.schema.json`).
Each recipe file starts with `"$schema": "../../schema/recipe.schema.json"`, so VS Code
and other editors validate and autocomplete it as you type, and any JSON Schema
validator (ajv, python-jsonschema…) can check it. `recipes.py validate` checks the
schema first, then the household rules.

The fields map one-to-one onto the v2 HTML template (`RECIPE-HTML-SPEC.md`), so
nothing about the house style is lost — a v2 HTML file can be converted to JSON
and back without changing a word (the test suite checks this for every recipe).

## Example

```json
{
  "slug": "breakfast-moong-dal-chilla",
  "category": "breakfast",
  "title": "Moong Dal Chilla",
  "subtitle": "High-protein · Night prep · 2 adults + toddler",
  "badges": ["Jain Vegetarian", "Toddler-adapted"],
  "labels": ["Lentil"],
  "meta": ["Night prep: 5 min (soak)", "Morning: 25 min", "Makes 6–7 chillas"],
  "protein": "~18–22g protein per adult serving (3 chillas)",
  "nightPrep": {
    "label": "Night Before",
    "items": ["Rinse moong dal and soak in water overnight (minimum 6 hrs)"]
  },
  "ingredientGroups": [
    {
      "label": "Batter",
      "items": [
        {"name": "Yellow moong dal (split, skinned)", "amount": "1 cup"},
        {"name": "Green chili, finely chopped", "amount": "1 (adults only)"}
      ]
    }
  ],
  "method": [
    {"type": "step", "title": "Make batter (night before)", "items": [
      "Blend with water {⅓ cup} until smooth — should coat a spoon but pour easily"
    ]},
    {"type": "toddler", "label": "Toddler — set aside now (night before)", "items": [
      "Remove ⅓ cup of batter before adding green chili"
    ]},
    {"type": "tip", "label": "Tip", "text": "If chillas tear, the tawa isn't hot enough."}
  ],
  "tags": ["High-protein", "Night prep", "Toddler-adapted"],
  "added": "2026-09-06"
}
```

## Fields

| Field | Required | v2 HTML element | Notes |
|---|---|---|---|
| `slug` | yes | file name | `<category>-<dish>`, lowercase, hyphens. Becomes the URL: `/recipes/<slug>.html`. |
| `category` | yes | file-name prefix | One of `breakfast curry dal rice bread snack chaat powder sweet drink`. Drives the **Type** filter. |
| `title` | yes | `<h1>` and `.recipe-name` | |
| `name` | no | `.recipe-name` | Only when the `<h2>` differs from the `<h1>` (e.g. "Sambar Powder (Sambar Masala)"). |
| `subtitle` | yes | `.subtitle` | One line under the title; also the card blurb and meta description. |
| `badges` | no | `.badge` | Usually `["Jain Vegetarian", "Toddler-adapted"]`. |
| `labels` | no | `.recipe-tag` | The pill above the recipe name. `"Paneer · Curry"` renders as one pill but becomes two filters. |
| `meta` | no | `.recipe-meta` spans | Times and yield. `Label: 25 min` entries are read as prep/cook times; `Makes …`/`Serves …` as the yield. |
| `protein` | no | `.protein-bar` | |
| `nightPrep` | no | `.night-prep` | `{label, items}`. The 🌙 is added automatically. `null` when there's no night prep. |
| `ingredientsTitle` / `methodTitle` | no | `.section-title` | Only when not "Ingredients" / "Method". |
| `ingredientGroups` | yes | `.ingredient-group` | `[{label, items: [{name, amount}]}]`. Every `amount` must lead with a quantity the batch control can read (`1½ cups`, `2–3`, `200g`) or be a phrase like `to taste` — see *Scaling*. |
| `method` | yes | `.steps-block` children, in order | Blocks of `type` `step` (`title`, `items`), `toddler` (`label`, `items` — 👶 added automatically) and `tip` (`label`, `text`). Steps are numbered automatically. |
| `tags` | no | — | Front-page filters, from a fixed list (see below). Detected on import. |
| `added` | no | — | `YYYY-MM-DD`, for the "Newest" sort. Set on import. |

### Inline markup

Text inside method bullets, night-prep bullets, ingredient names and tips can use:

- `{⅓ cup}` → `<span class="amt">(⅓ cup)</span>` — the amber per-step amount. Scales with the batch.
- `{=~6–7 in}` → same look, but never scales (sizes, or when the rules below guess wrong).
- `**word**` → bold.

Everything else is plain text (HTML is escaped).

### Every instruction carries its quantity

Non-negotiable, and enforced: `validate` fails a recipe when a step *uses* a listed
ingredient without saying how much (`tools/dhanjas/mentions.py`). A use is an
ingredient named after a cooking verb — "Add hing…", "…, top with coriander",
"Drain the soaked dal…". Each one needs, before the next ingredient or the end of the
clause, one of:

| Write | When |
|---|---|
| `{¼ tsp}` | the amount used in this step |
| `{rest of the 1 cup}` | whatever earlier steps (often the toddler pull) left — states the total, and scales |
| `{from Step 1}` / `{all}` | an intermediate made earlier (the masala, the cooked dal) |
| `to taste`, `a pinch`, `a splash` | in the sentence itself |
| `{alongside}`, `{optional}`, `{as needed}` | the ingredient list's own wording for unmeasured items |

Descriptions ("the celery should stay crisp"), negations ("no chili has gone in
yet"), destinations ("add hing to the cold ghee") and mentions after "until" aren't
uses. The check reads prose, so it's a strong safety net rather than a proof;
`docs/DESIGN-v3.md` describes the fully structured version.

### Instruction checkboxes

Every night-prep, step and toddler line on the website has a checkbox. Tap anywhere
on a line to tick it while cooking. Ticks are remembered per recipe on that device,
and "Clear ticks" in the top bar resets them. Printed copies show empty boxes to tick
with a pen. This is site-only (`assets/checklist.js`): the recipe markup and the
standalone v2 export are unchanged.

### Scaling (1× / 2× / 3×)

Quantities stay human-written, and `tools/dhanjas/quantity.py` reads the numbers in
them at build time. Each number that grows with the batch is wrapped in an invisible
`<data class="q" data-q="1½" data-u="cups">` marker; `assets/scale.js` multiplies the
marked numbers in the browser and re-formats them (`⅓ cup` → `⅔ cup`, `1 pinch` →
`2 pinches`, `Makes 6–7` → `Makes 12–14`).

| Scales | Stays fixed |
|---|---|
| ingredient amounts · `{amounts}` in steps and night prep · yield in `meta` (`Makes 6–7 chillas`, `6 adult servings`) | times (`5 min`, `45 sec`) · per-piece amounts (`1 tsp per chilla`, `2 tbsp/roti`, `~2 tbsp each`) · sizes (`~1 inch layer`) · anything in brackets (`2–3 (1 milder)`) · `Step 1` · toddler boxes (she's one toddler however big the batch) · tips · the protein bar (it's per serving) |

Try it on any page with `?scale=2`. The visible 1×/2×/3× buttons are one switch
(`SHOW_SCALE_CONTROL` in `tools/dhanjas/render.py`). `python3 tools/recipes.py scaled
<slug> 2` previews a recipe's amounts at any factor, and the browser check verifies
the page shows exactly those.

### Tags

A fixed list, so filters never overlap the Type row or each other:

| Tag | Rule |
|---|---|
| **Quick** | 20 min or less in total (meals only, not spice powders) |
| **Night prep** | has a night-before box |
| **Meal prep** | every curry and dal (the 3× batch dishes), plus "Sunday batch" / bulk-batch recipes |
| **High-protein** | 15 g+ per adult serving, read from the protein bar |
| **No-cook** | says no-cook |
| **Instant Pot** | Instant Pot or pressure cooker in the method |
| **Air fryer** | Ninja Crispi / air fry in the method or appliance notes |
| **Oven** | baked |

Toddler-adapted isn't a tag — every recipe is. Dish labels like "Paneer · Curry"
stay on the page and in search. `python3 tools/recipes.py retag` recomputes tags
(keeping any you added by hand); `retag --reset` recomputes from scratch.

## Exports — reuse the data anywhere

Every recipe is published in three formats next to its page, and `export` writes
the same files locally:

| File | What it is |
|---|---|
| `/recipes/<slug>.html` | the web page (shared CSS, scaling) |
| `/recipes/<slug>.json` | the house format, validated by the JSON Schema |
| `/recipes/<slug>.jsonld` | schema.org Recipe — importable by recipe apps |
| `/assets/recipes.json` | every recipe's card data and full text, for search or other tools |

```sh
python3 tools/recipes.py export <slug> --format html     # standalone v2 file, stylesheet inlined
python3 tools/recipes.py export --all --format all       # every recipe, every format → export/
```

## The standard format: schema.org/Recipe

Every recipe page also carries a `<script type="application/ld+json">` block in
the [schema.org Recipe](https://schema.org/Recipe) vocabulary — the format Google
recipe results, Paprika, Mealie, Tandoor, Pestle, Apple/Google "save recipe" and most
recipe sites use. It is generated from the JSON, so it never drifts:

| schema.org | from |
|---|---|
| `name`, `description` | `title`, `subtitle` |
| `recipeCategory` | `category` |
| `recipeCuisine` | "Indian (Jain)" |
| `suitableForDiet` | `VegetarianDiet` |
| `keywords` | labels + tags + badges |
| `recipeYield` | the `Makes …` / `Serves …` meta entry |
| `prepTime`, `cookTime`, `totalTime` | parsed from `meta` |
| `nutrition.proteinContent` | parsed from `protein` |
| `recipeIngredient` | `"<amount> <name>"` per ingredient |
| `recipeInstructions` | `HowToSection` per night-prep / step / toddler box, `HowToStep` per bullet, `HowToTip` per tip |

So any recipe manager that can "import from URL" can pull these pages in with the
ingredients, steps and toddler notes intact.

We don't use schema.org JSON as the source file itself because it has nowhere to
put the parts that make these recipes yours — the toddler pull point, night prep,
amounts repeated in each step. The house JSON keeps those, and the schema.org
output is derived from it.
