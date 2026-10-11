"""Recipe data model shared by the importer, validator and site builder.

A recipe lives in data/recipes/<slug>.json. The shape mirrors the v2 HTML
template one-to-one, so a recipe can round-trip between the two:

    {
      "slug": "breakfast-moong-dal-chilla",
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

SLUG_RE = re.compile(r"^(%s)-[a-z0-9]+(-[a-z0-9]+)*$" % "|".join(CATEGORIES))

# Tag vocabulary the importer can detect on its own. Tags are free-form in the
# JSON — anything added by hand shows up as a filter too.
AUTO_TAGS = [
    ("High-protein", r"high[- ]protein"),
    ("Night prep", None),            # set when the recipe has a night-prep box
    ("Toddler-adapted", None),       # set when the method has a toddler box
    ("Meal prep", r"meal[- ]prep|3\s*[×x]\s*(adult )?serving|weekly prep|batch on (saturday|sunday)|sunday[- ]batch|make sunday"),
    ("Instant Pot", r"instant pot|\bIP\b"),
    ("Pressure cooker", r"pressure[- ]cook|whistles?\b"),
    ("Air fryer", r"air[- ]?fr(y|ied|ier|yer)|ninja crispi|\bcrispi\b"),
    ("Oven", r"\boven\b|\bbake[ds]?\b|\bbaking\b"),
    ("No-cook", r"no[- ]cook"),
]
APPLIANCE_TAGS = {"Instant Pot", "Pressure cooker", "Air fryer", "Oven"}

# Sabji/curry and dal are the weekend & mid-week batch dishes (3× adult serving).
MEAL_PREP_CATEGORIES = {"curry", "dal"}

# Recipe-tag pills ("Paneer · Curry") become separate filters; spelling variants merge.
TAG_ALIASES = {
    "high protein": "High-protein", "meal prep": "Meal prep", "no-cook": "No-cook", "no cook": "No-cook",
    "batch": "Batch", "bulk batch": "Batch", "spice blend": "Spice blend",
}

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
        elif any(w in key for w in ("cook", "morning", "bake", "fry", "pressure", "simmer")):
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
    text, appliances = _clauses(all_text(recipe)), _clauses(appliance_text(recipe))
    tags = []
    for name, pattern in AUTO_TAGS:
        if name == "Night prep":
            hit = bool(recipe.get("nightPrep"))
        elif name == "Toddler-adapted":
            hit = any(b["type"] == "toddler" for b in recipe.get("method", []))
        elif name == "Meal prep":
            hit = recipe.get("category") in MEAL_PREP_CATEGORIES or bool(re.search(pattern, text, re.I))
        else:
            hit = bool(re.search(pattern, appliances if name in APPLIANCE_TAGS else text, re.I))
        if hit:
            tags.append(name)
    return tags


def filter_tags(recipe):
    """Everything the front page can filter on: split recipe-tag pills plus tags."""
    out = []
    for raw in [part for label in recipe.get("labels", []) for part in label.split("·")] + recipe.get("tags", []):
        t = raw.strip()
        if not t:
            continue
        t = TAG_ALIASES.get(t.lower(), t[0].upper() + t[1:])
        if t.lower() not in (o.lower() for o in out):
            out.append(t)
    return out


def retag(recipe, previous=None):
    """Fresh auto tags, keeping any hand-added tags (anything outside AUTO_TAGS)."""
    auto = {name for name, _ in AUTO_TAGS}
    manual = [t for t in (previous if previous is not None else recipe.get("tags", [])) if t not in auto]
    return detect_tags(recipe) + [t for t in manual if t not in detect_tags(recipe)]
