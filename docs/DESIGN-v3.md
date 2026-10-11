# Design: structured ingredients and quantity references (v3)

Status: **built as format 3.** The input contract is [`RECIPE-SPEC.md`](RECIPE-SPEC.md);
`tools/dhanjas/portions.py` implements it. Rava upma and moong dal chilla are converted;
the other 18 recipes are still format 2 and render the same way. (The rest of this
document is the original proposal, kept for the reasoning.)

Update: the rule "every instruction carries its quantity" is now enforced on the
current format by a prose check (`tools/dhanjas/mentions.py`), and the 22 gaps it
found in the 20 recipes were fixed. This proposal is what would make the rule
*provable* rather than heuristic, and let "rest of" be computed instead of written.

## The question

Most recipe sites (indianhealthyrecipes.com and thousands of others) use the same
recipe card. Can we use it? And how do we make *every instruction carry its
quantity* — non-negotiable — in a way that scales to many recipes and makes
ingestion easy?

## What that recipe card is

It's **WP Recipe Maker** (WPRM), a WordPress plugin; its HTML uses `wprm-recipe-*`
class names. Under the skin it is two things:

1. **schema.org/Recipe JSON-LD** in the page head — the standard Google requires
   for recipe search results. That's why every recipe site looks alike: they're all
   feeding the same Google format. Tasty Recipes, Mediavine Create and others emit
   the same JSON-LD.
2. **A structured ingredient model.** Each ingredient line is stored as four
   fields — `amount` · `unit` · `name` · `notes` (`1 | cup | yellow moong dal | split, skinned`).
   That's what makes its servings adjuster, metric/US toggle and print view work: the
   numbers are data, not text.

Instructions in WPRM are plain text by default. Its premium **inline ingredients**
feature lets a step embed a *reference* to an ingredient, which renders with its
amount and changes when you change servings. That reference idea is the key to the
"quantity in every step" requirement.

**Can we use it?** Use the *model*, not the plugin (it's WordPress-only).
- We already emit the same schema.org JSON-LD on every page (`/recipes/<slug>.jsonld`),
  so any app or site that understands WPRM recipes understands ours.
- We can import *from* any WPRM/schema.org site (see Ingestion).
- What we take from WPRM's model: split ingredient fields, and references from
  steps to ingredients.

## Today vs the gap

Today ingredient amounts are text that a parser reads at build time (`quantity.py`).
That works for scaling, and every ingredient line is guaranteed a readable quantity.
But step quantities are **retyped text**:

```
"Blend with water {⅓ cup} until smooth"
```

Nothing links that `⅓ cup` to the water in the ingredient list. So nothing can
enforce the rule. Measured across the 20 current recipes:

- 307 step bullets; 123 have no amount at all.
- **56 bullets name an ingredient and carry no quantity** — mostly
  "add remaining rava", "stir in remaining peanuts", "add 1½ cups water"
  (written as prose, so it doesn't scale).

The prompt's spec says every mention must carry its amount. Text can't hold that line;
structure can.

## Proposal: steps reference ingredients

### 1. Ingredients get IDs and split fields

```json
"ingredients": [
  {"id": "moong", "group": "Batter", "name": "Yellow moong dal", "note": "split, skinned", "qty": "1", "unit": "cup"},
  {"id": "water", "group": "Batter", "name": "Water", "note": "for blending", "qty": "⅓–½", "unit": "cup"},
  {"id": "chili", "group": "Batter", "name": "Green chili", "note": "finely chopped", "qty": "1", "audience": "adult"},
  {"id": "salt",  "group": "Batter", "name": "Salt", "qty": "to taste"}
]
```

### 2. Step bullets reference ingredients with the portion used

```
"Blend {moong} with {water ⅓ cup} until smooth"
"Add {ginger 1 tsp}, {cumin ½ tsp}, {hing ¼ tsp}"
"Slowly add {rava rest} while stirring"
```

- `{id qty}` — this step uses that much.
- `{id}` — this step uses all of it.
- `{id rest}` — whatever earlier steps left. **The system computes it and prints it**:
  "Slowly add rava **(¾ cup)**". A cook never sees "remaining" without a number again.
- Toddler boxes use the same references and never scale.

It renders exactly as today, `water (⅓ cup)` in amber, so the v2 look doesn't change.

### 3. The rules become enforceable (validator errors, not warnings)

| Rule | Catches |
|---|---|
| A bullet that names an ingredient must reference it | "Drain soaked moong dal" with no amount |
| Every ingredient is used by at least one step | listed but never used |
| Portions across steps add up to the list amount (or `rest` closes it) | step totals that don't match the list (e.g. 2 tbsp listed, 3 tbsp used) |
| Adult-only ingredients (chili) appear only after the first toddler pull | chili before her portion is pulled |
| Root vegetables are referenced only inside toddler boxes | carrot in the adult pan |

Scaling, metric/US conversion, a shopping list for the week's meal prep and
per-serving nutrition all fall out of the same data.

## The architecture — concepts, not files

```
            ┌──────────── importers ─────────────┐
 v2 HTML ──▶│                                    │
 house JSON▶│                                    │      ┌─ renderers ───────────────┐
 schema.org▶│  canonical Recipe  ──▶  rules  ──▶ │ ───▶ │ v2 web page (shared CSS)  │
 (any site) │  (schema/recipe.schema.json)       │      │ standalone v2 file        │
 text/photo▶│        ▲                           │      │ schema.org JSON-LD        │
  via Claude│        │ quantity / units          │      │ cards + search index      │
            └────────┴───────────────────────────┘      │ (later) print, shopping   │
                                                        └───────────────────────────┘
```

| Concept | Owns | Today |
|---|---|---|
| **Canonical recipe** | the data contract; one JSON Schema | `schema/recipe.schema.json` v2 → bump to v3 |
| **Quantity & units** | parse, scale, format, (later) convert | `tools/dhanjas/quantity.py` + `assets/scale.js`, tested against each other |
| **Rules** | schema, Jain, toddler, density, quantity invariants — each a small independent check | `tools/dhanjas/validate.py` |
| **Importers** | anything → canonical draft | v2 HTML ✓, house JSON ✓; schema.org/WPRM next |
| **Renderers** | canonical → every output | page, standalone, JSON-LD, cards ✓ |
| **Checks** | the rendered result, in a real browser | `tools/browser-check.mjs` ✓ |

Each box changes independently. A new source format is one importer. A new
output (print card, shopping list) is one renderer. A new household rule is one rule.

## Ingestion, made easy

1. **Claude writes the canonical JSON directly** instead of HTML. The schema is the
   contract (Claude can be given it as a structured-output schema). There's nothing to
   parse and no class names to get exactly right, and validation errors point at a
   field ("step 2, bullet 3 mentions `rava` with no quantity").
2. **Import from any recipe URL:** `recipes.py import <url>` reads the page's
   schema.org JSON-LD (WPRM, Tasty, etc.). That gives a canonical draft with
   ingredients already split. Claude then adapts it to the house rules: Jain
   substitutions, 3× serving logic, toddler pulls, quantity references. The validator
   either passes it or sends it back with exact errors. The result opens as a pull
   request with screenshots, and merging publishes it.
3. **v2 HTML keeps working** through the existing importer, so nothing breaks during
   the switch.

## Migration of the 20 existing recipes

- Ingredients → split fields: automatic (the quantity parser already reads 100% of them).
- Step text → references: automatic name-matching links most mentions. The rest,
  including the 56 bullets above, come out as a review list. Claude fixes them and
  the validator confirms. You approve the content changes, because some are real
  recipe decisions (how much rava is "remaining").
- Bump the schema to v3. The renderers produce identical pages, and the browser
  check proves it pixel-for-pixel.

## Decisions needed

1. Adopt step → ingredient references (`{id qty}`, `{id}`, `{id rest}`) as the v3 format?
2. Switch the prompt's output from v2 HTML to v3 JSON (HTML import stays as a fallback)?
3. Build the URL importer now, or after migration?
