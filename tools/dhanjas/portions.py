"""Ingredient portions and references (recipe format 3). Spec: docs/RECIPE-SPEC.md.

An ingredient may be split into keyed portions:

    {"id": "rava", "name": "Rava (semolina / sooji)", "short": "rava", "amount": "1 cup",
     "portions": {"toddler": "3 tbsp", "main": "rest"}}

and every instruction names the ingredient and portion it uses:

    "Slowly add {@rava:main|remaining roasted rava} while stirring"
       → "Slowly add remaining roasted rava (¾ cup + 1 tbsp) while stirring"

`lower(recipe, k)` turns any recipe (format 2 or 3) into plain format-2 text at batch
size k — refs resolved, "rest" computed, adult amounts scaled, toddler portions
fixed. Pages, search, schema.org and the household checks all work on that.
"""

import copy
import re

from .quantity import format_q, parse_q, scale_text, tokens

REF = re.compile(r"\{@([a-z0-9][a-z0-9-]*)(?::([a-z0-9][a-z0-9-]*))?(?:\|([^{}]*))?\}")
AMT = re.compile(r"\{([^{}@][^{}]*)\}")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def is_toddler_key(key):
    return key.startswith("toddler")


def default_short(name):
    return re.sub(r"\(.*?\)", "", name).split(",")[0].strip().lower()


class Ingredient:
    def __init__(self, item):
        self.id = item.get("id", "")
        self.name = item["name"]
        self.short = item.get("short") or default_short(item["name"])
        self.amount = item["amount"]
        self.total = parse_q(self.amount)
        # a per-piece total ("1 tsp per chilla") never scales, nor do its portions
        self.fixed = self.amount.startswith("=") or (self.total is not None and not any(ok for _, ok in tokens(self.amount)))
        self.portions = dict(item.get("portions") or {})
        self.errors, self.warnings = [], []
        self._rest = None
        self._resolve()

    def _resolve(self):
        p = self.portions
        rests = [k for k, v in p.items() if v.strip().lower() == "rest"]
        if len(rests) > 1:
            self.errors.append("ingredient %r has %d 'rest' portions — at most one" % (self.id, len(rests)))
        if rests and is_toddler_key(rests[0]):
            self.errors.append("ingredient %r: the toddler portion can't be 'rest' — give it an amount" % self.id)
        measured = {k: parse_q(v) for k, v in p.items() if k not in rests}
        numeric = {k: q for k, q in measured.items() if q is not None}
        if self.fixed and not rests:
            return  # per-piece totals ("1 cup per bowl") describe one piece; portions aren't summed against them
        if self.total is None:
            if rests:
                self.errors.append("ingredient %r: 'rest' needs a measured total amount, not %r" % (self.id, self.amount))
            return
        bad = [k for k, q in numeric.items() if not q.compatible(self.total)]
        if bad:
            if rests:
                self.warnings.append("ingredient %r: portion(s) %s aren't in the same unit as %r, so 'rest' can't be "
                                     "computed and will read 'rest of the %s'" % (self.id, ", ".join(bad), self.amount, self.amount))
            return
        used = None
        for q in numeric.values():
            used = q if used is None else used + q
        if rests:
            rest = self.total - used if used is not None else self.total
            if not rest.positive():
                self.errors.append("ingredient %r: the other portions use up all of %r — nothing left for 'rest'" % (self.id, self.amount))
            else:
                self._rest = rest
        elif used is not None and p and not used.within(self.total) and not self.total.within(used):
            self.errors.append("ingredient %r: portions add up to %s but the ingredient list says %r"
                               % (self.id, format_q(used), self.amount))

    # ---- amounts at batch size k ----
    def toddler_q(self):
        qs = [parse_q(v) for k, v in self.portions.items() if is_toddler_key(k)]
        qs = [q for q in qs if q is not None and self.total is not None and q.compatible(self.total)]
        if not qs:
            return None
        out = qs[0]
        for q in qs[1:]:
            out = out + q
        return out

    def whole(self, k=1):
        if k == 1 or self.fixed:
            return self.amount.lstrip("=")
        toddler = self.toddler_q()
        if toddler is not None:
            return format_q((self.total - toddler) * k + toddler)
        return scale_text(self.amount, k)

    def portion(self, key, k=1, in_toddler_box=False):
        text = self.portions[key]
        if text.strip().lower() == "rest":
            if self._rest is None:
                return "rest of the " + _bare(self.whole(k))
            return format_q(self._rest * (1 if self.fixed else k))
        if k == 1 or self.fixed or is_toddler_key(key) or in_toddler_box:
            return text
        return scale_text(text, k)


def _bare(text):
    """Amount as shown inside an instruction: drop list-only notes in brackets and
    "per bowl"-style suffixes (the step itself says which bowl or piece)."""
    text = re.sub(r"\s*\([^)]*\)", "", text)
    return re.sub(r"\s+per\s+[a-z]+$", "", text.strip()).strip()


def ingredients(recipe):
    out = {}
    for g in recipe.get("ingredientGroups", []):
        for it in g.get("items", []):
            if it.get("id"):
                out[it["id"]] = Ingredient(it)
    return out


def refs(text):
    return list(REF.finditer(text or ""))


def check(recipe):
    """Format-3 rules: ids, portions, references. Returns (errors, warnings)."""
    errors, warnings = [], []
    E, W = errors.append, warnings.append
    seen = set()
    for g in recipe.get("ingredientGroups", []):
        for it in g.get("items", []):
            i = it.get("id")
            if not i:
                E("ingredient %r has no id — every ingredient needs one, e.g. %r" % (it.get("name"), re.sub(r"[^a-z0-9]+", "-", default_short(it.get("name", ""))).strip("-")))
            elif not ID_RE.match(i):
                E("ingredient id %r: use lowercase letters, digits and hyphens" % i)
            elif i in seen:
                E("ingredient id %r is used twice" % i)
            seen.add(i)
            for key in (it.get("portions") or {}):
                if not ID_RE.match(key):
                    E("ingredient %r: portion key %r — use lowercase letters, digits and hyphens" % (i, key))
    ings = ingredients(recipe)
    for ing in ings.values():
        errors += ing.errors
        warnings += ing.warnings

    used_whole, used_portion = set(), set()
    for where, text, toddler_box in _instruction_texts(recipe):
        for m in refs(text):
            i, key = m.group(1), m.group(2)
            if i not in ings:
                E("%s refers to {@%s}, which isn't in the ingredient list" % (where, i))
                continue
            if key is None:
                used_whole.add(i)
            elif key not in ings[i].portions:
                E("%s refers to {@%s:%s}, but %r has no %r portion (has: %s)"
                  % (where, i, key, i, key, ", ".join(ings[i].portions) or "none"))
            else:
                used_portion.add((i, key))
                if is_toddler_key(key) and not toddler_box and not re.search(r"toddler|\bher\b|set aside", text, re.I):
                    W("%s uses the toddler portion {@%s:%s} outside a toddler box — fine for 'set aside for the toddler', "
                      "otherwise check the key" % (where, i, key))
    for i, ing in ings.items():
        if not ing.portions and i not in used_whole:
            E("ingredient %r is listed but no instruction uses it — reference it as {@%s}" % (i, i))
        for key in ing.portions:
            if (i, key) not in used_portion:
                E("portion {@%s:%s} is never used — every portion must appear in an instruction" % (i, key))
    for g in recipe.get("ingredientGroups", []):
        for it in g.get("items", []):
            if not it.get("id") and "portions" in it:
                E("ingredient %r has portions but no id" % it.get("name"))
    return errors, warnings


def _instruction_texts(recipe):
    if recipe.get("nightPrep"):
        for t in recipe["nightPrep"].get("items", []):
            yield "night prep", t, False
    for b in recipe.get("method", []):
        label = b.get("title") or b.get("label") or b["type"]
        for t in b.get("items", []):
            yield "%s %r" % (b["type"], label), t, b["type"] == "toddler"
        if b.get("text"):
            yield "tip %r" % label, b["text"], False


def _resolve_text(text, ings, k, toddler_box, scale_amounts):
    def ref(m):
        ing = ings.get(m.group(1))
        key, label = m.group(2), m.group(3)
        if ing is None or (key and key not in ing.portions):
            return m.group(0)          # reported by check(); leave it visible
        amount = ing.portion(key, k, toddler_box) if key else (ing.whole(1 if toddler_box else k))
        name = label if label is not None else ing.short
        return "%s {%s}" % (name, _bare(amount))
    out = text
    if scale_amounts and k != 1 and not toddler_box:
        # hand-written {amounts} first; references below are already computed at k
        out = AMT.sub(lambda m: m.group(0) if m.group(1).startswith("=") else "{%s}" % scale_text(m.group(1), k), out)
    out = REF.sub(ref, out)
    # a reference that starts a line starts a sentence
    return out[:1].upper() + out[1:] if REF.match(text) else out


def lower(recipe, k=1):
    """Format-2 view of a recipe at batch size k (1, 2, 3…). Pure text, ready to render."""
    r = copy.deepcopy(recipe)
    v3 = r.pop("format", 2) == 3
    ings = ingredients(recipe) if v3 else {}
    for g in r.get("ingredientGroups", []):
        for it in g.get("items", []):
            if v3 and it.get("id") in ings:
                it["amount"] = ings[it["id"]].whole(k)
            elif k != 1 and not it["amount"].startswith("="):
                it["amount"] = scale_text(it["amount"], k)
            for extra in ("id", "short", "portions"):
                it.pop(extra, None)
    if k != 1:
        r["meta"] = [scale_text(m, k) for m in r.get("meta", [])]
    if r.get("nightPrep"):
        r["nightPrep"]["items"] = [_resolve_text(t, ings, k, False, True) for t in r["nightPrep"]["items"]]
    for b in r.get("method", []):
        toddler = b["type"] == "toddler"
        if "items" in b:
            b["items"] = [_resolve_text(t, ings, k, toddler, b["type"] == "step") for t in b["items"]]
        if b.get("text"):
            b["text"] = _resolve_text(b["text"], ings, 1, True, False)
    return r
