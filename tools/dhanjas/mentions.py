"""Every instruction carries its quantity.

Finds step bullets that *use* a listed ingredient without saying how much.

A use is an ingredient named after a cooking verb that starts the clause or follows a
list break ("Add hing…", "…, top with coriander", "Drain the soaked dal…"). It is
satisfied when an {amount} follows it before the next ingredient or the end of the
clause — "Add hing {¼ tsp}, curry leaves {8–10}" — or when the clause says "to taste",
"a pinch", "a splash" or "from Step 2". For things that aren't measured afresh (the
cooked dal, the masala from step 1) write {from Step 1} or {all}; any {…} counts.

Not uses: descriptions ("the celery should stay crisp"), negations ("no chili yet"),
destinations ("add hing to the cold ghee", "spoon into the lettuce cups"), mentions in
brackets, after "until", or inside hyphenated compounds ("tomato-cashew paste").
"""

import re

from .model import plain

STRIP = re.compile(r"\b(fresh|whole|dry|dried|raw|roasted|toasted|finely|very|thinly|roughly|chopped|grated|minced|"
                   r"sliced|diced|crumbled|cubed|julienned|crushed|plain|full-fat|regular|light|neutral|reduced-sodium|"
                   r"optional|extra|split|skinned|soaked|rinsed|warm|hot|chilled|cold|thick|mixed|aged|seedless|"
                   r"skin-on|white|heavy)\b", re.I)
GENERIC_TAIL = {"seeds", "seed", "powder", "leaves", "leaf", "oil", "juice", "flour", "paste", "sauce", "sticks", "stick"}

VERBS = (r"add|adding|stir in|stir|mix in|mix|fold in|fold|pour|toss|put|whisk|blend|grind|pulse|fry|roast|toast|"
         r"drain|rinse|soak|sprinkle|scatter|top with|top|garnish|spread|place|combine|season|finish with|finish|"
         r"dice|chop|slice|shred|julienne|grate|measure|warm|heat|melt|use|scoop|set aside|remove|serve|smear|"
         r"drizzle|crush|coat|cook|steam|simmer|dissolve|knead|wrap|return|transfer|divide|spoon|tie|line|hang|"
         r"unwrap|rub")
LEADING_VERB = re.compile(r"(^|[,:]\s*|\b(?:then|and|now|also|gently|slowly|quickly)\s+)(?:%s)\b" % VERBS, re.I)
DESTINATION = re.compile(r"\b(to|into|over|in|on|onto|from|with|for|of)\s+(the|her|each|a)\s+([\w-]+\s+)?$", re.I)
NEGATION = re.compile(r"\b(no|not|don't|without|yet|isn't|never)\b", re.I)
PHRASE = re.compile(r"\b(to taste|a pinch|pinch of|a splash|splash of|a spoonful|a few drops|as needed|a little|"
                    r"a handful|small handful|a drizzle|from step \d+|all of it)\b", re.I)
# "rinse under water", "soak in fresh water": a place, not a measured use — except
# after stir/mix/fold, where "in" belongs to the verb ("stir in the peanuts").
LOCATION = re.compile(r"\b(?<!stir )(?<!mix )(?<!fold )(under|in)\s+(?:[\w-]+\s+){0,3}$", re.I)
PROSE_NUMBER = re.compile(r"(\d|[¼½¾⅓⅔⅛])\s*(cups?|tbsp|tsp|g|ml)\b")
CLAUSE_BREAK = ";.—"


def _variants(term):
    out = {term}
    if term.endswith("ies"):
        out |= {term[:-3] + "i", term[:-3] + "y"}
    elif term.endswith("oes"):
        out.add(term[:-2])
    elif term.endswith("s") and not term.endswith("ss"):
        out.add(term[:-1])
    else:
        out |= {term + "s", term + "es"}
    return out


def terms(name):
    """'Yellow moong dal (split, skinned)' → {'yellow moong dal', 'moong dal', 'dal', …}."""
    base = re.sub(r"\(.*?\)", "", name).split(",")[0].lower()
    found = set()
    for alt in re.split(r"\s+or\s+|\s*/\s*|\s*\+\s*", base):
        words = STRIP.sub("", alt).split()
        if not words:
            continue
        found.add(" ".join(words))
        if len(words) >= 2:
            found.add(" ".join(words[-2:]))
            if words[-1] in GENERIC_TAIL:
                found.add(words[-2])          # cumin seeds → cumin
        if words[-1] not in GENERIC_TAIL:
            found.add(words[-1])              # paneer, ghee, rava
    out = set()
    for t in found:
        if len(t) > 2:
            out |= _variants(t)
    return out


def unquantified(recipe):
    """[(step title, bullet, ingredient word, why)] for every use without an amount."""
    vocab = {}                                  # term → ingredient line it came from
    for g in recipe.get("ingredientGroups", []):
        for it in g.get("items", []):
            for t in terms(it["name"]):
                vocab.setdefault(t.lower(), it["name"])
    if not vocab:
        return []
    pattern = re.compile(r"\b(%s)\b" % "|".join(sorted(map(re.escape, vocab), key=len, reverse=True)), re.I)
    problems = []
    for b in recipe.get("method", []):
        if b.get("type") != "step":
            continue
        for item in b.get("items", []):
            text = re.sub(r"\([^)]*\)", lambda m: " " * len(m.group(0)), item)   # brackets aren't uses
            mentions = list(pattern.finditer(text))
            for i, m in enumerate(mentions):
                clause_start = max(text.rfind(c, 0, m.start()) for c in CLAUSE_BREAK) + 1
                ends = [e for e in (text.find(c, m.end()) for c in CLAUSE_BREAK) if e != -1]
                clause_end = min(ends) if ends else len(text)
                lead, clause = text[clause_start:m.start()], text[clause_start:clause_end]
                nxt = mentions[i + 1] if i + 1 < len(mentions) else None
                same_line = (nxt is not None and re.fullmatch(r"\s*(and|or|,|/|&)\s*([\w-]+\s+)?", text[m.end():nxt.start()])
                             and vocab.get(m.group(0).lower()) == vocab.get(nxt.group(0).lower()))
                if (same_line   # "dal or split peas {1 cup}", "apple and pineapple {¾ cup}": one amount for one line
                        or not LEADING_VERB.search(lead.strip()) or NEGATION.search(clause) or DESTINATION.search(lead)
                        or LOCATION.search(lead)
                        or re.search(r"\b(until|once|when|as|before|after)\b", lead, re.I)
                        or text[m.start() - 1:m.start()] == "-" or text[m.end():m.end() + 1] == "-"):
                    continue
                end = min(mentions[i + 1].start() if i + 1 < len(mentions) else len(text), clause_end)
                if ("{" in text[m.end():end] or re.search(r"\}\s*(of\s+)?(the\s+)?[\w-]*\s*$", lead)
                        or PHRASE.search(clause)):
                    continue
                why = ("write the number as {…} so it scales"
                       if PROSE_NUMBER.search(re.sub(r"\{[^}]*\}", "", clause)) else "no quantity")
                problems.append((b.get("title", ""), plain(item), m.group(0), why))
    return problems
