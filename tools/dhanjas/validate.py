"""Checks a recipe against the household rules and the v2 template spec.

Errors block ingestion. Warnings (mostly the density budget) are printed but
do not fail the build — tighten the writing, never the CSS.
"""

import re

from . import portions, schema
from .model import CATEGORIES, RESERVED_SLUGS, SLUG_RE, TAG_NAMES, plain

NAME_MAX, AMOUNT_MAX = 34, 14   # characters; the v2 ingredient columns
from .mentions import unquantified
from .quantity import needs_quantity

# Never allowed, for anyone.
FORBIDDEN = [
    "onions?", "garlic", "shallots?", "leeks?", "scallions?", "spring onions?", "green onions?", "chives?",
    "lahsun", "pyaa?z", "kanda",
    "eggs?", "egg whites?", "egg yolks?", "chicken", "mutton", "lamb", "beef", "pork", "bacon", "ham",
    "fish", "prawns?", "shrimps?", "anchov(y|ies)", "gelatine?", "fish sauce",
]
# Root vegetables: fine in the toddler's portion only.
ROOT_VEG = [
    "potato(es)?", "sweet potato(es)?", "aloo", "carrots?", "gajar", "beets?", "beetroots?", "turnips?",
    "radish(es)?", "mooli", "yams?", "taro", "arbi", "cassava", "parsnips?", "jicama", "suran",
]
# Allowed by the user's rules but often avoided in Jain kitchens — flag for a second look.
SECOND_LOOK = ["mushrooms?", "honey", "yeast"]

# Phrases that mention a restricted item without using it.
NEGATION = re.compile(r"\b(no|not|without|instead of|replaces?|substitutes?|substitute for|skip|in place of|free|swap(ped)?|standing in for)\b|→", re.I)

ADULT_HEAT = re.compile(r"\b(green chil(l)?i|red chil(l)?i|chil(l)?i (powder|flakes)|chil(l)?is?\b|cayenne|black pepper|kashmiri)", re.I)


def _rx(words):
    return re.compile(r"\b(%s)\b" % "|".join(words), re.I)


FORBIDDEN_RE, ROOT_RE, SECOND_RE = _rx(FORBIDDEN), _rx(ROOT_VEG), _rx(SECOND_LOOK)
TODDLER_RE = re.compile(r"toddler|\bher\b|for her|kid|child", re.I)


def check(recipe):
    errors, warnings = [], []
    E, W = errors.append, warnings.append

    # ---- shape: schema/recipe.schema.json ----
    errors += schema.check(recipe)

    # ---- format 3: ingredient ids, portions and {@id:key} references ----
    if recipe.get("format") == 3:
        e3, w3 = portions.check(recipe)
        errors += e3
        warnings += w3
        for title, bullet, word, why in unquantified(recipe, refs_only=True):
            E("step %r uses %r without a reference — write {@id} or {@id:key} so the quantity comes from the "
              "ingredient list: %s" % (title, word, bullet))
        raw = recipe
        recipe = portions.lower(recipe, 1)
    else:
        raw = None

    # ---- structure ----
    slug = recipe.get("slug", "")
    if not SLUG_RE.match(slug):
        E("slug %r must be the dish name in lowercase words joined by hyphens, e.g. rava-upma" % slug)
    elif slug in RESERVED_SLUGS:
        E("slug %r is one of the site's own names — pick another" % slug)
    if recipe.get("category") not in CATEGORIES:
        E("category %r isn't one of: %s" % (recipe.get("category"), ", ".join(CATEGORIES)))
    for field in ("title", "subtitle"):
        if not recipe.get(field):
            E("missing %s" % field)
    if not recipe.get("labels"):
        W("no recipe-tag label (e.g. Lentil, Paneer, Yogurt)")
    if not recipe.get("meta"):
        W("no meta line (times / yield)")
    if not recipe.get("protein"):
        W("no protein bar")

    groups = recipe.get("ingredientGroups") or []
    if not groups:
        E("no ingredient groups")
    for g in groups:
        if not g.get("label"):
            E("ingredient group without a label")
        for it in g.get("items", []):
            if not it.get("name"):
                E("ingredient without a name in group %r" % g.get("label"))
            if not it.get("amount"):
                E("ingredient %r has no amount" % it.get("name"))
            elif needs_quantity(it["amount"]):
                # The 1×/2× control can only scale a number it can read.
                E("ingredient %r: amount %r has no quantity to scale — write it as '1 tsp', '2–3', "
                  "'200g'… or use 'to taste' / 'a pinch' / 'as needed' / 'optional'" % (it.get("name"), it["amount"]))

    method = recipe.get("method") or []
    steps = [b for b in method if b.get("type") == "step"]
    tips = [b for b in method if b.get("type") == "tip"]
    if not steps:
        E("method has no steps")
    for b in method:
        if b.get("type") not in ("step", "toddler", "tip"):
            E("unknown method block type %r" % b.get("type"))
        if b.get("type") in ("step", "toddler") and not b.get("items"):
            E("%s %r has no bullets" % (b["type"], b.get("title") or b.get("label")))
        for item in b.get("items", []):
            if item.count("{") != item.count("}"):
                E("unbalanced amount braces in: %s" % item)

    # ---- Jain + toddler compliance ----
    def scan(text, where, toddler_ok, report=E):
        for sentence in re.split(r"(?<=[.;!?])\s+", plain(text)):
            scan_sentence(sentence, where, toddler_ok or bool(TODDLER_RE.search(sentence)), report)

    def scan_sentence(t, where, toddler_ok, report):
        if NEGATION.search(t):
            return  # "no onion needed", "hing replaces garlic", "Onion → celery", ...
        for m in FORBIDDEN_RE.finditer(t):
            report("restricted ingredient %r in %s: %s" % (m.group(0), where, t))
        if not toddler_ok:
            for m in ROOT_RE.finditer(t):
                report("root vegetable %r outside a toddler portion, in %s: %s" % (m.group(0), where, t))
        for m in SECOND_RE.finditer(t):
            W("double-check %r for Jain compliance, in %s" % (m.group(0), where))

    for g in groups:
        for it in g.get("items", []):
            toddler_ok = bool(TODDLER_RE.search(g.get("label", "") + " " + it.get("name", "") + " " + it.get("amount", "")))
            scan(it.get("name", ""), "ingredient group %r" % g.get("label"), toddler_ok)
    if recipe.get("nightPrep"):
        for item in recipe["nightPrep"].get("items", []):
            scan(item, "night prep", bool(TODDLER_RE.search(item)))
    for b in method:
        where = "%s %r" % (b["type"], b.get("title") or b.get("label"))
        for item in b.get("items", []):
            scan(item, where, b["type"] == "toddler")
        if b.get("text"):
            # Tips explain substitutions ("most jarred brands list garlic") — they can't
            # put an ingredient in the dish, so a hit there is only worth a second look.
            scan(b["text"], where, False, report=W)

    toddler_idx = [i for i, b in enumerate(method) if b.get("type") == "toddler"]
    if toddler_idx and recipe.get("category") == "powder":
        pass  # pantry blends: the toddler box is a usage note, there's no pan to pull from
    elif toddler_idx:
        for b in method[:toddler_idx[0]]:
            if b.get("type") != "step":
                continue
            pulled = False  # "set aside her portion before adding chili" earlier in the same step
            for item in b.get("items", []):
                t = plain(item)
                if TODDLER_RE.search(t):
                    pulled = True
                elif ADULT_HEAT.search(t) and not pulled and not NEGATION.search(t) and not re.search(r"\bbowl\b", t, re.I):
                    # (a sauce whisked in a separate bowl never touches her portion)
                    W("chili/pepper goes in before the first toddler box (step %r): %s" % (b.get("title"), t))
                    break
    elif "toddler" in (recipe.get("subtitle", "") + " ".join(recipe.get("badges", []))).lower():
        W("header mentions the toddler but the method has no toddler box")

    # ---- every instruction carries its quantity (non-negotiable) ----
    for title, bullet, word, why in ([] if raw else unquantified(recipe)):
        E("step %r uses %r without a quantity (%s) — e.g. \"add %s {¼ cup}\", "
          "\"{rest of the 1 cup}\", \"{from Step 1}\" or \"to taste\": %s" % (title, word, why, word, bullet))

    # ---- tags ----
    for t in recipe.get("tags", []):
        if t not in TAG_NAMES:
            W("tag %r isn't in the tag list (%s) — it won't show as a filter" % (t, ", ".join(TAG_NAMES)))

    # ---- density budget ----
    if not 3 <= len(groups) <= 5:
        W("density: %d ingredient groups (budget 3–5)" % len(groups))
    for g in groups:
        n = len(g.get("items", []))
        if not 4 <= n <= 8:
            W("density: group %r has %d lines (budget 4–8)" % (g.get("label"), n))
    if not 2 <= len(steps) <= 4:
        W("density: %d steps (budget 2–4)" % len(steps))
    for b in steps:
        n = len(b.get("items", []))
        if not 4 <= n <= 8:
            W("density: step %r has %d bullets (budget 4–8)" % (b.get("title"), n))
    if len(tips) != 1:
        W("density: %d tip boxes (budget 1)" % len(tips))
    # ingredient lines sit in narrow columns: longer than this and they wrap awkwardly
    for g in groups:
        for it in g.get("items", []):
            if len(it.get("name", "")) > NAME_MAX:
                W("field length: ingredient name %r is %d characters (keep to %d)" % (it["name"], len(it["name"]), NAME_MAX))
            amount = it.get("amount", "").lstrip("=")
            if len(amount) > AMOUNT_MAX:
                W("field length: amount %r for %r is %d characters (keep to %d) — put \"per bowl\" in the name "
                  "or group label and mark the amount fixed with '='" % (amount, it.get("name"), len(amount), AMOUNT_MAX))

    return errors, warnings
