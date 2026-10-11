# Recipe format

Every recipe is one JSON file in `data/recipes/<slug>.json`. It is the source of
truth: the recipe page, the front-page card, the search index and the
schema.org metadata are all generated from it.

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
| `ingredientGroups` | yes | `.ingredient-group` | `[{label, items: [{name, amount}]}]`. |
| `method` | yes | `.steps-block` children, in order | Blocks of `type` `step` (`title`, `items`), `toddler` (`label`, `items` — 👶 added automatically) and `tip` (`label`, `text`). Steps are numbered automatically. |
| `tags` | no | — | Front-page filters. Detected on import (see below); add your own freely. |
| `added` | no | — | `YYYY-MM-DD`, for the "Newest" sort. Set on import. |

### Inline markup

Text inside method bullets, night-prep bullets, ingredient names and tips can use:

- `{⅓ cup}` → `<span class="amt">(⅓ cup)</span>` — the amber per-step amount.
- `**word**` → bold.

Everything else is plain text (HTML is escaped).

### Tags

On import the tool detects: **High-protein**, **Night prep**, **Toddler-adapted**,
**Meal prep** (every curry/dal, plus "Sunday batch" style recipes), **Instant Pot**,
**Pressure cooker**, **Air fryer**, **Oven**, **No-cook**. Appliance tags only come from
the method, meta and appliance tips, and negated mentions ("no air fryer needed")
are ignored. Anything else you put in `tags` is kept — `python3 tools/recipes.py retag`
recomputes the detected ones without touching yours.

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
