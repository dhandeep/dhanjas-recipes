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
