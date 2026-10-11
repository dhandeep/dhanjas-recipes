"""Quantities inside amount text, so a 1×/2×/3× control can scale a recipe.

Amounts stay human-written ("1½ cups", "2–3, deseeded", "1 tsp per chilla"). This
module finds the number(s) in them and decides which ones scale with the batch:

  scales     1½ cups · 400g · 8–10 · 2 stalks · 3 pinches · 1 (adults only)
  fixed      5 min · 45 sec (times)       1 tsp per chilla · 2 tbsp/roti · ~2 tbsp each (per piece)
             ~1 inch layer · ~6–7 in (sizes)    (1 milder) (anything in brackets)
             2× · 330°F · Step 1
  no number  to taste · a pinch · rest · from Step 1

Start an amount with "=" in the JSON ("{=~6–7 in}") to force it fixed when the rules
guess wrong. Toddler boxes never scale — she's one toddler however big the batch.

assets/scale.js re-implements format() for the browser; tests and the browser check
make sure the two agree.
"""

import re
from fractions import Fraction

GLYPHS = {"¼": Fraction(1, 4), "½": Fraction(1, 2), "¾": Fraction(3, 4), "⅓": Fraction(1, 3), "⅔": Fraction(2, 3),
          "⅛": Fraction(1, 8), "⅜": Fraction(3, 8), "⅝": Fraction(5, 8), "⅞": Fraction(7, 8)}
G = "".join(GLYPHS)
NUM = r"(?:\d+\s?[%s]|\d+ \d+/\d+|\d+/\d+|\d+(?:\.\d+)?|[%s])" % (G, G)

UNITS = [
    "cups", "cup", "tbsp", "tsp", "kg", "g", "ml", "l", "oz", "lb", "inches", "inch", "in", "cm",
    "pinches", "pinch", "sprigs", "sprig", "stalks", "stalk", "heads", "head", "leaves", "halves",
    "medium", "large", "small", "whole",
    # fixed — never scaled
    "minutes", "minute", "mins", "min", "seconds", "second", "secs", "sec", "hours", "hour", "hrs", "hr",
    "whistles", "whistle",
]
TIME = {"minutes", "minute", "mins", "min", "seconds", "second", "secs", "sec", "hours", "hour", "hrs", "hr",
        "whistles", "whistle"}
PLURAL = {"cup": "cups", "pinch": "pinches", "sprig": "sprigs", "stalk": "stalks", "head": "heads", "inch": "inches"}
SINGULAR = {v: k for k, v in PLURAL.items()}

TOKEN = re.compile(
    r"(?P<lo>%s)(?:(?P<sep>\s?[–-]\s?)(?P<hi>%s))?(?:(?P<sp>\s?)(?P<unit>%s)(?![A-Za-z]))?"
    % (NUM, NUM, "|".join(UNITS)))
PER_PIECE = re.compile(r"\s*(/|per\b|each\b|×|x\b|°)", re.I)
SIZE = re.compile(r"\s*(layer|thick|wide|across|diameter|long)\b", re.I)
NO_NUMBER_OK = re.compile(
    r"^(to taste|as needed|a pinch|pinch|tiny pinch|a handful|small handful|handful|optional|alongside|rest|"
    r"from step \d+|for \w+.*)$", re.I)


def value(text):
    text = text.strip()
    if " " in text and "/" in text:
        whole, frac = text.split(" ", 1)
        return int(whole) + Fraction(frac)
    if "/" in text:
        return Fraction(text)
    if text[-1] in GLYPHS:
        return (int(text[:-1].strip()) if len(text) > 1 else 0) + GLYPHS[text[-1]]
    return Fraction(text)


def tokens(text):
    """[(match, scalable)] for every number in an amount string."""
    if text.startswith("="):
        return [(m, False) for m in TOKEN.finditer(text)]
    out, depth = [], 0
    pos = 0
    for m in TOKEN.finditer(text):
        before = text[pos:m.start()]
        depth += before.count("(") - before.count(")")
        pos = m.start()
        after = text[m.end():]
        unit = m.group("unit") or ""
        scalable = not (
            depth > 0
            or unit in TIME
            or PER_PIECE.match(after)
            or SIZE.match(after)
            or (unit == "in" and not after.strip())
            or text[:m.start()].rstrip().lower().endswith("step")
        )
        out.append((m, scalable))
    return out


def has_quantity(text):
    return any(s for _, s in tokens(text))


def needs_quantity(text):
    """True when an ingredient amount neither scales nor is a recognised 'to taste'-type phrase."""
    t = text.strip()
    return not tokens(t) and not NO_NUMBER_OK.match(t)


def fmt(v, unit=""):
    v = Fraction(v)
    if unit in ("g", "ml") and v >= 50:
        return str(int(round(v / 5) * 5))
    if unit in ("g", "ml", "kg", "l", "oz", "lb") and v.denominator != 1 and v > 10:
        return str(int(round(v)))
    whole = int(v)
    frac = v - whole
    best = min([Fraction(0), Fraction(1)] + list(GLYPHS.values()), key=lambda f: abs(f - frac))
    if best == 1:
        whole, best = whole + 1, Fraction(0)
    glyph = next((g for g, f in GLYPHS.items() if f == best), "")
    if not whole:
        return glyph or "0"
    return "%d%s" % (whole, glyph)


def unit_for(unit, v):
    if not unit:
        return unit
    if v > 1:
        return PLURAL.get(unit, unit)
    return SINGULAR.get(unit, unit)


def scale_token(m, factor):
    lo, hi = value(m.group("lo")) * factor, (value(m.group("hi")) * factor if m.group("hi") else None)
    unit = m.group("unit") or ""
    s = fmt(lo, unit)
    if hi is not None:
        s += m.group("sep") + fmt(hi, unit)
    if unit:
        s += (m.group("sp") or "") + unit_for(unit, hi if hi is not None else lo)
    return s


def scale_text(text, factor):
    """Plain-text scaling, used by tests and `recipes.py scaled`."""
    out, last = [], 0
    for m, ok in tokens(text):
        out.append(text[last:m.start()])
        out.append(scale_token(m, factor) if ok else m.group(0))
        last = m.end()
    out.append(text[last:])
    return "".join(out).lstrip("=")


# ---------------------------------------------------------------------------
# Arithmetic for ingredient portions (format 3): "1 cup" − "3 tbsp" = "¾ cup + 1 tbsp".

VOLUME_TSP = {"tsp": 1, "tbsp": 3, "cup": 48, "cups": 48}
MASS_G = {"g": 1, "kg": 1000}
CUP_FRACTIONS = [Fraction(0), Fraction(1, 4), Fraction(1, 3), Fraction(1, 2), Fraction(2, 3), Fraction(3, 4)]


class Q:
    """A measured amount in a base unit: tsp for volume, g for mass, else a count
    ('', 'medium', 'stalk', …). hi is set for ranges."""

    def __init__(self, lo, hi=None, kind=""):
        self.lo, self.hi, self.kind = Fraction(lo), (Fraction(hi) if hi is not None else None), kind

    def compatible(self, other):
        return other is not None and self.kind == other.kind

    def _pair(self):
        return self.lo, (self.hi if self.hi is not None else self.lo)

    def __add__(self, other):
        (a, b), (c, d) = self._pair(), other._pair()
        hi = b + d if (self.hi is not None or other.hi is not None) else None
        return Q(a + c, hi, self.kind)

    def __sub__(self, other):
        # subtracting a fixed portion from a total: low − low, high − high
        (a, b), (c, d) = self._pair(), other._pair()
        hi = b - d if (self.hi is not None or other.hi is not None) else None
        return Q(a - c, hi, self.kind)

    def __mul__(self, k):
        return Q(self.lo * k, self.hi * k if self.hi is not None else None, self.kind)

    def positive(self):
        return self.lo > 0

    def within(self, other):
        """self's range fits inside other's (exact amounts must be equal)."""
        (a, b), (c, d) = self._pair(), other._pair()
        return a >= c and b <= d

    def __repr__(self):
        return "Q(%s, %s, %r)" % (self.lo, self.hi, self.kind)


def parse_q(text):
    """The leading quantity of an amount as a Q, or None ('to taste', 'a pinch').
    Added volumes count in full: '¾ cup + 1 tbsp'."""
    head, plus, tail = text.partition(" + ")
    if plus:
        a, b = parse_q(head), parse_q(tail)
        if a is not None and b is not None and a.kind == b.kind == "volume" and a.hi is None and b.hi is None:
            return a + b
    m = TOKEN.match(text.strip().lstrip("~≈ "))
    if not m:
        return None
    unit = (m.group("unit") or "").lower()
    if unit in TIME:
        return None
    lo, hi = value(m.group("lo")), (value(m.group("hi")) if m.group("hi") else None)
    if unit in VOLUME_TSP:
        f, kind = VOLUME_TSP[unit], "volume"
    elif unit in MASS_G:
        f, kind = MASS_G[unit], "mass"
    else:
        f, kind = 1, SINGULAR.get(unit, unit)
    return Q(lo * f, hi * f if hi is not None else None, kind)


def _fmt_volume(tsp):
    """Readable kitchen volume: cups when it's a clean cup fraction or more than ½ cup,
    tablespoons below that, teaspoons for small amounts; remainders are added on
    ('¾ cup + 1 tbsp')."""
    tsp = Fraction(tsp)
    cups = tsp / 48
    whole, frac = int(cups), cups - int(cups)
    if tsp >= 12 and frac in CUP_FRACTIONS:
        return fmt(cups) + (" cups" if cups > 1 else " cup")
    if tsp > 24:
        # largest cup fraction that leaves a clean ½-tablespoon remainder
        # (the leftover stays under ¼ cup, so it reads as tablespoons)
        candidates = sorted((f for f in CUP_FRACTIONS if f <= frac and (frac - f) * 48 < 12), reverse=True)
        below = next((f for f in candidates if ((tsp - (whole + f) * 48) / Fraction(3, 2)).denominator == 1), candidates[0])
        main = whole + below
        rest = tsp - main * 48
        return fmt(main) + (" cups" if main > 1 else " cup") + (" + " + _fmt_volume(rest) if rest > 0 else "")
    if tsp >= 3:
        tbsp = tsp / 3
        if (tbsp * 2).denominator == 1:                 # whole or half tablespoons
            return fmt(tbsp) + " tbsp"
        whole_tbsp = int(tbsp)
        return "%d tbsp + %s" % (whole_tbsp, _fmt_volume(tsp - whole_tbsp * 3))
    return fmt(tsp) + " tsp"


def format_q(q):
    def one(v):
        if q.kind == "volume":
            return _fmt_volume(v)
        if q.kind == "mass":
            return fmt(v, "g") + "g"
        unit = unit_for(q.kind, v) if q.kind else ""
        return fmt(v) + (" " + unit if unit else "")
    if q.hi is None or q.hi == q.lo:
        return one(q.lo)
    lo, hi = one(q.lo), one(q.hi)
    # "⅔ cup" + "1 cup" → "⅔–1 cup" when both share a simple unit
    lo_parts, hi_parts = lo.rsplit(" ", 1), hi.rsplit(" ", 1)
    if len(lo_parts) == 2 and len(hi_parts) == 2 and "+" not in lo + hi and \
            SINGULAR.get(lo_parts[1], lo_parts[1]) == SINGULAR.get(hi_parts[1], hi_parts[1]):
        return "%s–%s" % (lo_parts[0], hi)
    if " " not in lo + hi:
        return "%s–%s" % (lo, hi)      # plain counts / grams: "10–13", "200–250g"
    return "%s – %s" % (lo, hi)
