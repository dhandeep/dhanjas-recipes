"""Checks a recipe against the household rules and the v2 template spec.

Errors block ingestion. Warnings (mostly the density budget) are printed but
do not fail the build — tighten the writing, never the CSS.
"""

import re

from .model import AMT_RE, CATEGORIES, SLUG_RE, plain

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

    # ---- structure ----
    slug = recipe.get("slug", "")
    if not SLUG_RE.match(slug):
        E("slug %r must be <category>-<dish> with a known prefix: %s" % (slug, ", ".join(CATEGORIES)))
    if recipe.get("category") != slug.split("-", 1)[0]:
        E("category %r does not match the slug prefix" % recipe.get("category"))
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
    if toddler_idx and recipe.get("category") != "powder":  # pantry blends: the toddler box is a usage note
        for b in method[:toddler_idx[0]]:
            if b.get("type") != "step":
                continue
            pulled = False  # "set aside her portion before adding chili" earlier in the same step
            for item in b.get("items", []):
                t = plain(item)
                if TODDLER_RE.search(t):
                    pulled = True
                elif ADULT_HEAT.search(t) and not pulled and not NEGATION.search(t):
                    W("chili/pepper goes in before the first toddler box (step %r): %s" % (b.get("title"), t))
                    break
    elif "toddler" in (recipe.get("subtitle", "") + " ".join(recipe.get("badges", []))).lower():
        W("header mentions the toddler but the method has no toddler box")

    # ---- every ingredient mention in a step carries its amount ----
    for b in steps:
        for item in b.get("items", []):
            if not AMT_RE.search(item) and re.search(r"\b(add|stir in|mix in|fold in|pour)\b", item, re.I):
                W("bullet adds something but carries no {amount}: %s" % plain(item))

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

    return errors, warnings
