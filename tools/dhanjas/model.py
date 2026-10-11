"""Recipe data model shared by the importer, validator and site builder.

A recipe lives in data/recipes/<slug>.json. The shape mirrors the v2 HTML
template one-to-one, so a recipe can round-trip between the two:

    {
      "slug": "moong-dal-chilla",
      "category": "breakfast",
      "title": "Moong Dal Chilla",           # <h1> and <h2 class="recipe-name">
      "subtitle": "High-protein · Night prep · 2 adults + toddler",
      "badges": ["Jain Vegetarian", "Toddler-adapted"],
      "labels": ["Lentil"],                  # .recipe-tag pills
      "meta": ["Night prep: 5 min (soak)", "Morning: 25 min", "Makes 6–7 chillas"],
      "protein": "~18–22g protein per adult serving (3 chillas)",
      "nightPrep": {"label": "Night Before", "items": ["..."]},   # or null
      "ingredientGroups": [{"label": "Batter", "items": [{"name": "...", "amount": "1 cup"}]}],
      "method": [
        {"type": "step", "title": "Make batter", "items": ["Blend with water {⅓ cup}"]},
        {"type": "toddler", "label": "Toddler — set aside now", "items": ["..."]},
        {"type": "tip", "label": "Tip", "text": "..."}
      ],
      "tags": ["High-protein", "Night prep", "Toddler-adapted"],   # front-page filters
      "added": "2026-09-06"
    }

Inline text (method bullets, night-prep bullets, ingredient names, tips) uses
two tiny markers:  {⅓ cup}  renders as <span class="amt">(⅓ cup)</span>, and
**word** renders bold. Everything else is plain text and gets HTML-escaped.
"""

import re

# Filename prefix -> display name, in front-page order. Matches the prefix
# table in RECIPE-HTML-SPEC.md.
CATEGORIES = {
    "breakfast": "Breakfast",
    "curry": "Curry & Sabji",
    "dal": "Dal",
    "rice": "Rice",
    "bread": "Bread",
    "snack": "Snack",
    "chaat": "Chaat",
    "powder": "Powders & Chutneys",
    "sweet": "Sweet",
    "drink": "Drink",
}

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# pages live at the site root (/<slug>), so a slug can't be one of the site's own names
RESERVED_SLUGS = {"index", "404", "assets", "data", "docs", "schema", "tools", "inbox", "export",
                  "screenshots", "recipes", "node_modules", "cname"}

# The only tags the site uses — a short, fixed list so filters never overlap the
# Type row or each other. Detected on import; any of these can also be added by
# hand. Dish labels ("Paneer · Curry") stay on the page and in search, not here.
# Every recipe is toddler-adapted by design, so that isn't a tag.
TAGS = [
    ("Quick", "20 minutes or less, start to finish"),
    ("Night prep", "has a night-before step"),
    ("Meal prep", "weekend / mid-week batch dish (every curry and dal) or made ahead in bulk"),
    ("High-protein", "15 g+ protein per adult serving"),
    ("No-cook", "assembled, nothing cooked on the day"),
    ("Instant Pot", "Instant Pot or pressure cooker"),
    ("Air fryer", "uses the Ninja Crispi"),
    ("Oven", "baked"),
]
TAG_NAMES = [name for name, _ in TAGS]

PATTERNS = {
    "Meal prep": r"meal[- ]prep|3\s*[×x]\s*(adult )?serving|weekly prep|batch on (saturday|sunday)|sunday[- ]batch|make sunday",
    "High-protein": r"high[- ]protein",
    "No-cook": r"no[- ]cook",
    "Instant Pot": r"instant pot|\bIP\b|pressure[- ]cook|whistles?\b",
    "Air fryer": r"air[- ]?fr(y|ied|ier|yer)|ninja crispi|\bcrispi\b",
    "Oven": r"\boven\b|\bbake[ds]?\b|\bbaking\b",
}
APPLIANCE_TAGS = {"Instant Pot", "Air fryer", "Oven"}
MEAL_PREP_CATEGORIES = {"curry", "dal"}
QUICK_MINUTES = 20
HIGH_PROTEIN_GRAMS = 15

AMT_RE = re.compile(r"\{([^{}]+)\}")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def plain(text):
    """Inline markup -> plain text, keeping amounts in parentheses."""
    text = AMT_RE.sub(lambda m: "(%s)" % m.group(1), text)
    return BOLD_RE.sub(lambda m: m.group(1), text)


def minutes(text):
    """'25 min' -> 25, '1 hr 10 min' -> 70, '20–25 min' -> 25. None if no time."""
    total, found = 0, False
    for lo, hi, unit in re.findall(r"(\d+(?:\.\d+)?)(?:\s*[–-]\s*(\d+(?:\.\d+)?))?\s*(hours?|hrs?|minutes?|mins?)\b", text, re.I):
        val = float(hi or lo)
        total += val * 60 if unit.lower().startswith("h") else val
        found = True
    return int(round(total)) if found else None


def times(recipe):
    """Best-effort prep/cook/total minutes from the meta line, for schema.org."""
    out = {}
    for entry in recipe.get("meta", []):
        label, _, value = entry.partition(":")
        if not value:
            mins = minutes(entry)  # a bare "~45 min" is the total
            if mins is not None:
                out["total"] = mins
            continue
        mins = minutes(value)
        if mins is None:
            continue
        key = label.strip().lower()
        if "soak" in key:
            continue  # passive time; would swamp the "quickest" sort
        if "total" in key:
            out["total"] = mins
        elif any(w in key for w in ("cook", "morning", "bake", "fry", "pressure", "simmer", "roast", "steam")):
            out["cook"] = out.get("cook", 0) + mins
        elif any(w in key for w in ("prep", "night", "batch", "active")):
            out["prep"] = out.get("prep", 0) + mins
    if "total" not in out and ("prep" in out or "cook" in out):
        out["total"] = out.get("prep", 0) + out.get("cook", 0)
    return out


def yield_text(recipe):
    for entry in recipe.get("meta", []):
        if re.match(r"\s*(makes|serves|yield)\b", entry, re.I) or "serving" in entry.lower():
            return entry.strip()
    return None


def protein_grams(recipe):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:[–-]\s*(\d+(?:\.\d+)?))?\s*g\b", recipe.get("protein") or "")
    if not m:
        return None
    return m.group(1) + ("–" + m.group(2) if m.group(2) else "")


def all_text(recipe):
    """Every human-readable string in the recipe, for tag detection and search."""
    parts = [recipe.get("title", ""), recipe.get("subtitle", ""), recipe.get("protein") or ""]
    parts += recipe.get("badges", []) + recipe.get("labels", []) + recipe.get("meta", [])
    if recipe.get("nightPrep"):
        parts += recipe["nightPrep"].get("items", [])
    for g in recipe.get("ingredientGroups", []):
        parts.append(g.get("label", ""))
        parts += [i.get("name", "") for i in g.get("items", [])]
    for block in recipe.get("method", []):
        parts += [block.get("title", ""), block.get("label", ""), block.get("text", "")]
        parts += block.get("items", [])
    return plain(" \n".join(p for p in parts if p))


NEGATED = re.compile(r"\b(no|not|without|skip|instead of|no need)\b|n't\b", re.I)


def appliance_text(recipe):
    """Where an appliance mention means the recipe actually uses it: header, meta,
    night prep, steps and toddler boxes, plus tips about appliances. Other tips are
    often usage notes ("great on air-fryer paneer") and would give false tags."""
    parts = [recipe.get("title", ""), recipe.get("subtitle", "")] + recipe.get("meta", [])
    if recipe.get("nightPrep"):
        parts += recipe["nightPrep"].get("items", [])
    for block in recipe.get("method", []):
        if block["type"] == "tip":
            if re.search(r"applian|equipment|tool", block.get("label", ""), re.I):
                parts.append(block.get("text", ""))
        else:
            parts += [block.get("title", ""), block.get("label", "")] + block.get("items", [])
    return plain("\n".join(p for p in parts if p))


def _clauses(text):
    # Clause by clause so "no air fryer needed" / "Instant Pot isn't useful" don't tag.
    return "\n".join(c for c in re.split(r"[.;:—\n]|\s–\s", text) if not NEGATED.search(c))


def detect_tags(recipe):
    from .portions import lower        # format-3 refs → plain text first
    recipe = lower(recipe)
    text = _clauses(all_text(recipe))
    labels = " ".join(recipe.get("labels", []))
    appliances = _clauses(appliance_text(recipe))
    hits = {
        "Quick": recipe.get("category") != "powder" and (times(recipe).get("total") or 999) <= QUICK_MINUTES,
        "Night prep": bool(recipe.get("nightPrep")),
        "Meal prep": (recipe.get("category") in MEAL_PREP_CATEGORIES or bool(re.search(PATTERNS["Meal prep"], text, re.I))
                      or bool(re.search(r"meal[- ]prep|\bbatch\b", labels, re.I))),
        "High-protein": (protein_per_adult(recipe) or 0) >= HIGH_PROTEIN_GRAMS or bool(re.search(PATTERNS["High-protein"], text, re.I)),
    }
    # "no-cook" is itself a negation, so it's matched before the negation filter.
    hits["No-cook"] = bool(re.search(PATTERNS["No-cook"], all_text(recipe) + " " + labels, re.I))
    for name in ("Instant Pot", "Air fryer", "Oven"):
        hits[name] = bool(re.search(PATTERNS[name], appliances if name in APPLIANCE_TAGS else text, re.I))
    return [name for name in TAG_NAMES if hits.get(name)]


def protein_per_adult(recipe):
    """Lower bound of '~18–22g protein per adult …' — None when the bar isn't per adult serving."""
    text = recipe.get("protein") or ""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:[–-]\s*\d+(?:\.\d+)?)?\s*g\b[^·—]*per adult", text)
    return float(m.group(1)) if m else None


def retag(recipe, previous=None):
    """Fresh detected tags plus any vocabulary tag that was added by hand. Tags
    outside the vocabulary are dropped (the validator reports them)."""
    detected = detect_tags(recipe)
    kept = [t for t in (previous if previous is not None else recipe.get("tags", [])) if t in TAG_NAMES]
    return [t for t in TAG_NAMES if t in detected or t in kept and t not in AUTO_ONLY]


# Tags whose rule is objective — a stale hand-set value shouldn't survive a retag.
AUTO_ONLY = {"Quick", "Night prep"}
