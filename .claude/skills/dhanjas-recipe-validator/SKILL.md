---
name: dhanjas-recipe-validator
description: >
  Validate a dhanjas.com recipe JSON file (format 3, docs/RECIPE-SPEC.md) for cooking
  logic, toddler timing, Jain compliance, scaling sense and format conformance.
  Run it automatically at the end of every recipe generation, conversion or edit,
  before the file is committed to inbox/; don't wait to be asked. Also run it when
  the user says "check the recipe", "validate", "audit" or "does this make sense".
---

# dhanjas.com recipe validator (format 3)

Run this at the end of every recipe generation or edit, before committing the JSON
to `inbox/<dish>.json` in `dhandeep/dhanjas-recipes`. Work through every check and
think like a cook, not a linter. Quote the exact text when flagging an issue.

Some rules are enforced mechanically by `python3 tools/recipes.py validate`:
- every ingredient and portion is used
- portions add up and `rest` is computed
- every listed ingredient used in an instruction is written as a reference
- the schema, Jain words, density and field lengths

If you can run it (Claude Code in the repo), run it first and fix its ✗ errors.
This skill covers what a script can't judge. If you can't run it, do Check 10 by
hand as well.

## What to read
- **Ingredients:**
  - every item's `id`, `name`, `short`, `amount` and `portions`, group by group
  - which portions are toddler keys (any key starting with `toddler`) and which is `rest`
- **Method:**
  - night-prep items
  - every step in order (numbered automatically: toddler boxes and tips don't get numbers)
  - each toddler box's position relative to the steps
  - the tip
- **References:**
  - read every `{@id}`, `{@id:key}` and `{@id:key|words}` as the cook will see it, e.g. "ginger (1 tsp)"
  - plain `{amounts}` and `{=fixed amounts}`

---

## Check 1: Used but not listed
Every ingredient a step uses must be on the list, with a reference. Look for
ingredients that slipped in as plain words:
- "add a splash of lemon"
- "garnish with sesame"
- "grease with oil" when no oil is listed

Flag **"Used but not listed"**.

Allowed without a listing: water for washing or soaking, a splash of water to
loosen, "salt to taste" when salt is listed.

## Check 2: Second add of the same thing
The same reference may appear twice on purpose, for example "Rinse {@rava}" then
"Add {@rava}", or celery prepped in one step and added in the next. For every id or
portion referenced more than once, confirm the second mention isn't a **second
add**. Flag **"Possible duplicate add"** and quote both lines.

Highest risk: hing, ginger, tomato paste, cream, kasuri methi, garam masala, salt.

## Check 3: Set aside and return
For every "set aside", "transfer to a plate", "remove and keep", find where it comes
back. Paneer and capsicum set aside for the toddler must reach her box. Adult
paneer set aside must return with its `main` or `rest` portion. Flag **"Set aside but
never returned"**.

## Check 4: Toddler timing (anything hot)
Find the first toddler box. Before it, nothing hot may touch the shared pan, batter
or base. Hot includes:
- chili powder, fresh or dried chilies, chili paste
- **spice blends ground with dried chilies** (kadai masala, sambar powder, garam masala blends with chili)
- **black or white pepper**
- chili flakes, gochugaru, chili crisp, gochujang

If her portion comes from a component made ahead (a chutney powder, a sauce), her
share must be set aside **before** the heat goes into that component.

Sauces whisked in a separate bowl, or condiments served at the table, don't count.
A `powder` recipe has no pan to pull from; its toddler box is a usage note
("¼ tsp max per serving").

Flag **"Toddler portion pulled too late"** and quote the hot line and the pull.

## Check 5: Step references
Check every "from Step N", "Step N", "returns in Step N" against the numbered steps.
Toddler boxes and tips are not numbered. Flag **"Invalid step reference"**.

## Check 6: Portions make sense
The arithmetic is automatic. Check the meaning:
- Each portion key names a real moment: `tempering` is used in the tempering, `garnish` at the end.
- **Toddler portions** are used only in toddler boxes or in "set aside … for the toddler" lines.
- **`rest`** is used where the cook really adds what's left, not where a fresh measured amount is meant.
- A portion that's a phrase ("a drop", "a splash") is genuinely tiny, not hiding a real amount.
- Her portion is a sensible size for a 2-year-old next to the adult amount.

Flag **"Portion mismatch"**.

## Check 7: Jain compliance
Adult ingredients, steps and night prep must contain none of:
- onion, pyaaz, shallot, leek, spring/green onion, chives
- garlic, lahsun
- potato, carrot, beet, turnip, radish, parsnip, yam, sweet potato
- eggs, meat, poultry, fish, gelatin
- honey, mushrooms

Exceptions:
- Ginger is fine.
- Potato and carrot are allowed only in toddler portions or toddler boxes, and must be marked "(toddler)" in the name.
- Watch hidden sources: bouillon cubes, store gochujang, chili crisp, some wrappers (egg), Worcestershire.

In tips, describe substitutions as "onion → celery + hing", and say "aren't Jain"
rather than naming what's in a product.

Flag **"Jain violation"** with the exact text. If a cooked base or tempering has no
hing, flag a warning.

## Check 8: Toddler box logic
- The box pulls her portion before adult heat, or confirms it was pulled earlier.
- It must **not** say to skip hing: **hing is fine for her**.
- It must **not** forbid potato or carrot: **both are allowed for her**.
- Everything it uses is on the list, as a toddler portion.
- Textures are safe: no whole nuts, cut into strips or small pieces, soft.
- Every recipe has at least one toddler box. If absent, flag **"Missing toddler section"**.

## Check 9: Reads right as a cook
Walk through it at the stove:
- Is the pan on the heat before things go in?
- Does each step assume the right state from the one before?
- Do times, temperatures and appliances match the household? The Ninja Crispi runs hot with a 330°F floor; the Instant Pot is available.
- Does the yield in `meta` match the quantities?
- Read each reference as rendered, e.g. "Add remaining paneer (375g)". Does the sentence read naturally, with no doubled words ("yogurt (a small bowl) of yogurt")?

Flag **"Sequence inconsistency"** or **"Reads wrong"**, quoting the lines.

## Check 10: Format conformance
| Must be true | Flag if not |
|---|---|
| `"format": 3` and `"$schema": "https://recipes.dhanjas.com/schema/recipe.schema.json"` | "Format header" |
| File name `<dish>.json` equals `slug`, named after the dish, with no category prefix (`rava-upma`, not `breakfast-rava-upma`) | "Slug off-convention" |
| `category` is one of breakfast, curry, dal, rice, bread, snack, chaat, powder, sweet, drink | "Bad category" |
| Every ingredient has a unique `id`; `amount` leads with a quantity or is to taste / a pinch / as needed / optional / alongside | "Ingredient field" |
| Every instruction that uses a listed ingredient uses a reference, never a typed amount (`Add salt {½ tsp}` is wrong; `Add {@salt}` is right) | "Typed amount" |
| The reference is the mention: `Add {@ginger}`, not `Add ginger {@ginger}` | "Doubled mention" |
| Plain `{…}` only for things not on the list (intermediates, times, `{from Step 1}`) | "Plain amount on a listed ingredient" |
| No HTML in any field; no `tags` or `added` (filled on import) | "Extra fields" |

## Check 11: Scaling sense
Read the recipe at **2×**:
- Batch amounts double.
- Toddler portions stay the same.
- Per-piece and per-bowl amounts stay the same: use `"=…"`, or "per bowl" in the name or group label.
- Things that must not double are fixed with `{=…}` or `"=…"`:
  - steam water in the Instant Pot
  - tin depth (`{=~1 inch layer}`)
  - one chilla's pour (`{=¼ cup}`)
  - the size of a dough ball
  - pressure-cook and natural-release times
- "Two adult bowls" style wording still makes sense.

Flag **"Scales wrong"**.

## Check 12: Density and field length
| | Budget | Flag |
|---|---|---|
| Ingredient groups | 3–5 | "Group count" |
| Lines per group | 4–8 | "Group size" |
| Steps | 2–4 | "Too many / too few steps" |
| Bullets per step | 4–8 | "Step size" |
| Toddler boxes | 1–2 | — |
| Tip boxes | 1 | "Too many tips" |
| Ingredient `name` | ≤ 34 characters | "Name too long — will wrap" |
| Ingredient `amount` | ≤ 14 characters | "Amount too long — move 'per bowl' into the name or label, mark it '='" |

These are warnings. Fix by tightening words, merging steps at the same station,
folding storage lines into the last step, or folding notes into the one tip. Never
drop content the cook needs.

---

## Report

### Recipe validation: [Recipe name]

**[N] errors · [M] warnings · [P] checks passed**

#### Errors (fix before committing)
> **[Check]**: one-line description
> Text: "[quote]" (vs "[quote]")
> Fix: [specific correction, written as the JSON change]

#### Warnings (review)
> **[Check]**: one-line description. Context: [note]

#### Passed
- Check 1 Used but not listed ✓
- …

If nothing is found: **All 12 checks passed. Ready to commit to `inbox/<dish>.json`.**

Fix every error in the JSON before committing. Never commit a recipe with unfixed
errors. When a fix changes the recipe itself (an amount, an ingredient, the toddler
pull), tell the user what changed.

---

## Common failure patterns

| Pattern | Example | Check |
|---|---|---|
| Spice blend with chilies goes in before the pull | kadai masala bloomed, then "pull before chili powder" | 4 |
| Pepper in a shared batch | makhana batch roast seasoned with black pepper | 4 |
| Her chutney made with the adults' chili | toddler box: "use chutney made without chili", but none was set aside | 4 |
| Ingredient named in a step with no listing | "grease with oil" | 1 |
| Second add | "bloom {@hing}" in step 2 and "add {@hing}" in step 4 | 2 |
| Set-aside paneer never returns | step 2 sets aside, finish forgets `{@paneer:main}` | 3 |
| Toddler key used for an adult | `{@ghee:toddler}` in an adult step | 6 |
| Typed amount beside a listed ingredient | `Add salt {½ tsp}` | 10 |
| Steam water doubles at 2× | `Add {@water-steam}` without `"=1½ cups"` | 11 |
| "per bowl" in the amount | `"2 tbsp per bowl"` (15 characters) | 12 |
| "Skip hing for her" | hing is fine at 2 | 8 |
| "No potato for her" | potato and carrot are allowed for her | 8 |
