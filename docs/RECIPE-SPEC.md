# Recipe spec — format 3 (input contract)

This is the contract for writing a dhanjas.com recipe. Whoever writes the recipe
(you, or Claude from the recipe prompt) produces **one JSON file** that follows it.
The website, the 1×/2×/3× batch control, the instruction checkboxes, the
schema.org data and every validation check are generated from that file.

The household rules — Jain diet, toddler adaptations, serving logic, appliances —
stay in the recipe prompt. This spec covers **how a recipe is written down**.

Machine-readable version: [`schema/recipe.schema.json`](../schema/recipe.schema.json).
Checked by `python3 tools/recipes.py validate`.

---

## 1. The one idea

> **Every ingredient is listed once, with its total. If it's used in more than one
> place, the total is split into keyed portions. Every instruction names the
> ingredient — and the portion — it uses.**

```
ingredient list:   Rava     1 cup      →  portions:  toddler = 3 tbsp,  main = rest
instruction:       "Slowly add {@rava:main|remaining roasted rava} while stirring"
reader sees:       "Slowly add remaining roasted rava (¾ cup + 1 tbsp) while stirring"
```

Nobody ever writes "remaining" without a number again: `rest` is computed
(1 cup − 3 tbsp = ¾ cup + 1 tbsp), it changes correctly at 2× and 3×, and the
toddler's 3 tbsp stays 3 tbsp because she's one toddler however big the batch.

---

## 2. The file

- One recipe per file, named `<dish>.json` — the same name as the slug (`rava-upma.json`). No category prefix.
- Categories (the `category` field): `breakfast` `curry` `dal` `rice` `bread` `snack` `chaat` `powder` `sweet` `drink`.
- Publish by committing it to `inbox/` in the `dhandeep/dhanjas-recipes` repo (see `docs/INGEST.md`).

| Field | Required | What it is |
|---|---|---|
| `"$schema"` | recommended | `"https://recipes.dhanjas.com/schema/recipe.schema.json"` — editors then check the file as you type |
| `"format"` | **yes** | `3` |
| `slug` | yes | the dish name, lowercase, hyphens: `rava-upma`. The page is `recipes.dhanjas.com/<slug>` |
| `category` | yes | one of the categories above; drives the Type filter |
| `title` | yes | dish name (page heading) |
| `name` | no | only if the recipe-name heading differs from the title |
| `subtitle` | yes | one line under the title |
| `badges` | no | usually `["Jain Vegetarian", "Toddler-adapted"]` |
| `labels` | no | the small pill above the name, e.g. `["Paneer · Curry"]` |
| `meta` | no | times and yield, e.g. `"Morning: 20 min"`, `"Makes 6–7 chillas"` (yields scale, times don't) |
| `protein` | no | the protein bar, e.g. `"~18–22g protein per adult serving"` |
| `nightPrep` | no | `{"label": "Night Before", "items": [...]}` or `null` |
| `ingredientGroups` | yes | see §3 |
| `method` | yes | see §4 |
| `tags`, `added` | no | filled in on import |

---

## 3. Ingredients

```json
"ingredientGroups": [
  {"label": "Main", "items": [
    {"id": "rava", "name": "Rava (semolina / sooji)", "short": "rava", "amount": "1 cup",
     "portions": {"toddler": "3 tbsp", "main": "rest"}},
    {"id": "ginger", "name": "Fresh ginger, grated", "short": "ginger", "amount": "1 tsp"}
  ]}
]
```

| Field | Rule |
|---|---|
| `id` | **Required.** Unique in the recipe; lowercase letters, digits, hyphens: `rava`, `green-chili`, `ghee`. If the same ingredient appears on two list lines (e.g. ghee for the base and ghee for the gravy), give each its own id: `ghee-base`, `ghee-gravy`. |
| `name` | Exactly as the ingredient list should read: `"Rava (semolina / sooji)"`. |
| `short` | How instructions name it: `"rava"`. Optional — defaults to the name before any comma or bracket, lowercased. |
| `amount` | **The total for the batch.** Leads with a quantity — `"1 cup"`, `"2–3"`, `"400g"`, `"1½ tbsp"`, `"1 (adults only)"` — or is one of: `"to taste"`, `"a pinch"`, `"as needed"`, `"optional"`, `"alongside"`. A per-piece amount (`"1 tsp per chilla"`, `"2 tbsp per bowl"`) never scales; inside instructions the "per …" is dropped. Prefix `=` to stop an amount scaling. |
| `portions` | Only when the ingredient is used in more than one place, or partly by the toddler. See below. |

### Portions

A map of **key → amount**, in the order they're used:

```json
"portions": {"toddler": "3 tbsp", "main": "rest"}          // rava: toddler's share, then the rest
"portions": {"blend": "⅓ cup", "adjust": "1–2 tbsp"}       // water: two moments
"portions": {"tempering": "2 tbsp", "toddler": "a drop"}   // ghee: a phrase is fine for tiny amounts
"portions": {"grease": "½ tsp", "drizzle": "½ tsp"}        // per-chilla ghee: inherits "per chilla", never scales
"portions": {"toddler": "1–2 tbsp"}                        // toddler-only ingredient (boiled potato)
```

- **Keys** are short words for the moment or the person: `toddler`, `main`, `tempering`, `garnish`, `blend`, `adjust`, `grease`, `drizzle`, `batter`, `gravy`, `dough`, `filling`.
- **`toddler`** — any key starting with `toddler` (`toddler`, `toddler-dough`) is her portion. It **never scales**.
- **`rest`** — at most one portion may be `"rest"`. It is computed as the total minus the other measured portions, and needs those portions in the same kind of unit as the total (volume, weight or count). Never use `rest` for the toddler.
- **They must add up.** Measured portions (plus `rest`) must equal the total. A range total holds them if the sum fits inside it (`⅓ cup` + `1–2 tbsp` fits `⅓–½ cup`). Phrases (`"a drop"`, `"tiny pinch"`) aren't counted.
- **Every portion must be used** by at least one instruction.

---

## 4. Instructions

`method` is the page's method section, in order:

```json
{"type": "step",    "title": "Tempering", "items": ["...", "..."]}
{"type": "toddler", "label": "Toddler — pull portion here (before chili)", "items": ["..."]}
{"type": "tip",     "label": "Tip", "text": "..."}
```

Steps are numbered automatically. A toddler box goes exactly where her portion is
pulled, before any chili goes into the pan. Night-prep items follow the same rules.

### References — the non-negotiable rule

**Every time an instruction uses a listed ingredient, it is written as a reference:**

| Write | Means | Reader sees |
|---|---|---|
| `{@ginger}` | the whole amount | ginger **(1 tsp)** |
| `{@rava:toddler}` | one portion | rava **(3 tbsp)** |
| `{@rava:main\|remaining roasted rava}` | a portion, named your way | remaining roasted rava **(¾ cup + 1 tbsp)** |

- The reference *is* the ingredient's mention — write `Add {@ginger}`, not `Add ginger {@ginger}`.
- The words after `|` replace the `short` name, so the sentence reads naturally: `{@rava:toddler|roasted rava}`, `{@chili|Kashmiri chilies}`.
- A reference at the start of a line is capitalised automatically.
- Notes in brackets on the list amount (`"1 (adults only)"`) are dropped inside instructions (shows as **(1)**).
- `{@id}` is allowed for an ingredient with portions too — it means the whole amount (e.g. "Rinse {@rava}" before it's split).

### Amounts that aren't ingredients

Things that aren't on the ingredient list are written as plain amounts in braces:

| Write | For |
|---|---|
| `{3–4 tbsp}` | an intermediate: "Scoop out the cooked vegetables {3–4 tbsp}" — scales |
| `{5 min}`, `{45 sec}` | times — never scale |
| `{=~¼ cup}` | per piece / a size: "Pour {=~¼ cup} and spread" — `=` stops it scaling |
| `{from Step 1}` | something made earlier: "Add the masala {from Step 1}" |

Never type an amount next to a listed ingredient (`Add salt {½ tsp}`) — that's an
error, because it can drift from the ingredient list. Use `{@salt}`.

Descriptions that don't use an ingredient need nothing: "Cook until the rava absorbs all water".

---

## 5. Batch size (1× / 2× / 3×)

| Scales | Stays fixed |
|---|---|
| ingredient totals, adult portions, `rest` (recomputed), plain `{amounts}` in steps and night prep, yields in `meta` | toddler portions and everything in toddler boxes, per-piece amounts, `{=…}`, times, tips, the protein bar |

The list total at 2× is 2 × (total − toddler) + toddler, so the list and the
instructions always agree.

---

## 6. Checklist (what `validate` enforces)

- [ ] `"format": 3`, valid slug and category
- [ ] every ingredient has a unique `id` and an `amount` that leads with a quantity (or `to taste` / `a pinch` / `as needed` / `optional` / `alongside`)
- [ ] portions add up to the amount; at most one `rest`; `rest` leaves something
- [ ] every ingredient and every portion is referenced at least once
- [ ] every reference points to a real id and portion key
- [ ] no instruction uses a listed ingredient without a reference
- [ ] household rules: no onion, garlic, eggs or meat; root vegetables only in toddler portions; toddler box before chili (warning)
- [ ] density budget: 3–5 groups of 4–8 lines, 2–4 steps of 4–8 bullets, 1 tip (warnings)

---

## 7. Worked example — the complete file

`data/recipes/rava-upma.json`:

```json
{
  "$schema": "https://recipes.dhanjas.com/schema/recipe.schema.json",
  "format": 3,
  "slug": "rava-upma",
  "category": "breakfast",
  "title": "Rava Upma with Peanuts",
  "subtitle": "A quick semolina upma, roasted golden and studded with peanuts.",
  "badges": [
    "Jain Vegetarian",
    "Toddler-adapted"
  ],
  "labels": [
    "Semolina"
  ],
  "meta": [
    "Night prep: none",
    "Morning: 20 min",
    "Serves 2 adults + toddler"
  ],
  "protein": "~14–16g protein per adult serving (peanuts are the primary source)",
  "nightPrep": null,
  "ingredientGroups": [
    {
      "label": "Main",
      "items": [
        {"id": "rava", "name": "Rava (semolina / sooji)", "short": "rava", "amount": "1 cup", "portions": {"toddler": "3 tbsp", "main": "rest"}},
        {"id": "peanuts", "name": "Raw peanuts", "short": "peanuts", "amount": "⅓ cup", "portions": {"toddler": "1 tsp", "main": "rest"}},
        {"id": "water", "name": "Water", "short": "water", "amount": "2¾ cups", "portions": {"toddler": "¼ cup", "main": "2½ cups"}},
        {"id": "ginger", "name": "Fresh ginger, grated", "short": "ginger", "amount": "1 tsp"},
        {"id": "green-chili", "name": "Green chili, slit", "short": "green chili", "amount": "1–2 (adults)"},
        {"id": "ghee", "name": "Ghee", "short": "ghee", "amount": "2 tbsp", "portions": {"tempering": "2 tbsp", "toddler": "a drop"}}
      ]
    },
    {
      "label": "Tempering",
      "items": [
        {"id": "mustard", "name": "Mustard seeds", "short": "mustard seeds", "amount": "1 tsp"},
        {"id": "cumin", "name": "Cumin seeds", "short": "cumin seeds", "amount": "½ tsp"},
        {"id": "hing", "name": "Hing", "short": "hing", "amount": "¼ tsp"},
        {"id": "curry-leaves", "name": "Curry leaves", "short": "curry leaves", "amount": "8–10"},
        {"id": "cashews", "name": "Cashews, optional", "short": "cashews", "amount": "10–12"}
      ]
    },
    {
      "label": "Vegetables",
      "items": [
        {"id": "capsicum", "name": "Capsicum, finely diced", "short": "capsicum", "amount": "½ cup"},
        {"id": "tomato", "name": "Tomato, chopped", "short": "tomato", "amount": "1 medium"},
        {"id": "turmeric", "name": "Turmeric", "short": "turmeric", "amount": "¼ tsp"},
        {"id": "salt", "name": "Salt", "short": "salt", "amount": "to taste"},
        {"id": "lemon", "name": "Lemon juice", "short": "lemon juice", "amount": "1 tsp"},
        {"id": "coriander", "name": "Fresh coriander", "short": "coriander", "amount": "2 tbsp"},
        {"id": "potato", "name": "Boiled potato, finely diced (toddler only)", "short": "boiled potato", "amount": "1–2 tbsp", "portions": {"toddler": "1–2 tbsp"}}
      ]
    }
  ],
  "method": [
    {
      "type": "step",
      "title": "Dry roast rava and peanuts",
      "items": [
        "Heat a wide pan on medium; add {@rava} — dry roast 3–4 min, stirring constantly until lightly golden and fragrant",
        "Remove and set aside",
        "In the same pan, dry roast {@peanuts} on medium 3–4 min until skins blister; set aside",
        "Let the peanuts cool, then rub off any loose skins"
      ]
    },
    {
      "type": "step",
      "title": "Tempering",
      "items": [
        "Heat {@ghee:tempering} in the pan on medium",
        "Add {@mustard} — splutter; add {@cumin}",
        "Add {@hing}, {@curry-leaves}, {@cashews} if using — stir 30 sec",
        "Add {@ginger} — cook 20 sec",
        "Add {@capsicum} and {@tomato}; cook 2 min",
        "Add {@turmeric} and {@salt}; stir"
      ]
    },
    {
      "type": "toddler",
      "label": "Toddler — pull portion here (before chili)",
      "items": [
        "Scoop out the cooked vegetables {3–4 tbsp} into a separate small pan now — before adding green chili to the main pan",
        "Add {@water:toddler} and roasted {@rava:toddler} to her pan; cook on low, stirring until soft and water absorbed",
        "Stir in crushed {@peanuts:toddler} or {@ghee:toddler}",
        "Optional: add {@potato:toddler|finely diced boiled potato} for extra bulk"
      ]
    },
    {
      "type": "step",
      "title": "Add chili and cook upma",
      "items": [
        "Add {@green-chili} to the adult pan; cook 20 sec",
        "Bring {@water:main} to a boil in a separate pot; pour into the tempering pan carefully",
        "Reduce heat to medium-low; slowly add {@rava:main|remaining roasted rava} while stirring continuously to avoid lumps",
        "Stir in {@peanuts:main|remaining roasted peanuts}",
        "Cover and cook 3–4 min on low until rava absorbs all water",
        "Finish with {@lemon} and {@coriander}"
      ]
    },
    {
      "type": "tip",
      "label": "Tip",
      "text": "Roasting rava before cooking is non-negotiable — it prevents lumpy upma. Add water slowly and stir constantly as it goes in."
    }
  ],
  "tags": [
    "Quick"
  ],
  "added": "2026-09-07"
}
```

How some of its lines read on the page:

| Written | At 1× | At 2× |
|---|---|---|
| `Heat a wide pan on medium; add {@rava} — dry roast…` | Heat a wide pan on medium; add rava **(1 cup)** | Heat a wide pan on medium; add rava **(1¾ cups + 1 tbsp)** |
| `Add {@water:toddler} and roasted {@rava:toddler} to her pan…` | Add water **(¼ cup)** and roasted rava **(3 tbsp)** to her pan | Add water **(¼ cup)** and roasted rava **(3 tbsp)** to her pan |
| `Bring {@water:main} to a boil…` | Bring water **(2½ cups)** to a boil in a separate pot | Bring water **(5 cups)** to a boil in a separate pot |
| `Slowly add {@rava:main\|remaining roasted rava}…` | …slowly add remaining roasted rava **(¾ cup + 1 tbsp)** | …slowly add remaining roasted rava **(1½ cups + 2 tbsp)** |
| `Stir in {@peanuts:main\|remaining roasted peanuts}` | Stir in remaining roasted peanuts **(5 tbsp)** | Stir in remaining roasted peanuts **(½ cup + 2 tbsp)** |

The toddler line is identical at both sizes; the main portions absorb the change.
A second example with night prep, a split water amount, toddler pinches and
per-chilla ghee: `data/recipes/moong-dal-chilla.json`.

---

## 8. For the recipe prompt

Replace the **Recipe Output Format** section of the recipe prompt with:

> ## Recipe Output Format
>
> Every recipe is one JSON file following **`RECIPE-SPEC.md` (format 3)** — read it
> before writing any recipe, and follow it exactly. In short:
>
> - Name the file `<dish>.json` (e.g. `rava-upma.json`, no category prefix); set `"format": 3` and a `category`.
> - List each ingredient once with an `id` and its **total** `amount`.
> - When an ingredient is used in more than one place — including the toddler's
>   share — split the total into keyed `portions` (`"toddler": "3 tbsp", "main": "rest"`).
>   Toddler portions never scale; `rest` is computed.
> - **Every instruction that uses an ingredient writes it as a reference:**
>   `{@id}` for the whole amount, `{@id:key}` for a portion, `{@id:key|words}` to
>   name it naturally. Never type an amount next to a listed ingredient.
> - Plain `{amount}` only for things that aren't ingredients (intermediates, times);
>   `{=amount}` for per-piece amounts that must not scale.
> - Steps as bullets, one action per bullet; toddler boxes inline at the moment her
>   portion is pulled, before chili; 3–5 ingredient groups, 2–4 steps, 1 tip.
>
> Commit the file to `inbox/<dish>.json` on `main` in
> `dhandeep/dhanjas-recipes`. The site validates it, builds the page (with batch
> scaling and checkboxes) and publishes it. If validation fails, the Action log says
> exactly which line to fix.
