"""python3 -m unittest discover -s tools"""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dhanjas import parse_html, render, schema, validate  # noqa: E402
from dhanjas.model import TAG_NAMES, detect_tags  # noqa: E402
from dhanjas.quantity import needs_quantity, scale_text, tokens  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RECIPES = sorted((ROOT / "data" / "recipes").glob("*.json"))
CSS = (ROOT / "assets" / "recipe.css").read_text("utf-8")


def load(name="breakfast-moong-dal-chilla"):
    r = json.loads((ROOT / "data" / "recipes" / ("%s.json" % name)).read_text("utf-8"))
    r.pop("$schema", None)
    return r


class RoundTrip(unittest.TestCase):
    def test_every_recipe_survives_render_and_parse(self):
        self.assertTrue(RECIPES)
        for path in RECIPES:
            want = json.loads(path.read_text("utf-8"))
            want.pop("$schema", None)
            for standalone in (False, True):
                got = parse_html.parse(render.recipe_page(want, CSS, standalone), want["slug"])
                for r in (want, got):
                    for k in ("tags", "added"):
                        r.pop(k, None)
                with self.subTest(slug=want["slug"], standalone=standalone):
                    self.assertEqual(want, got)

    def test_standalone_export_inlines_the_fixed_stylesheet(self):
        page = render.recipe_page(load(), CSS, standalone=True)
        self.assertIn(CSS.strip(), page)
        self.assertNotIn('rel="stylesheet"', page)

    def test_amount_markup(self):
        self.assertEqual(render.rich("Add salt {½ tsp} & **stir**", scale=False),
                         'Add salt <span class="amt">(½ tsp)</span> &amp; <strong>stir</strong>')
        self.assertEqual(render.rich("Add {½ tsp}"),
                         'Add <span class="amt">(<data class="q" data-q="½" data-u="tsp" data-sp=" ">½ tsp</data>)</span>')


class Validator(unittest.TestCase):
    def errors(self, recipe):
        return validate.check(recipe)[0]

    def test_all_recipes_pass(self):
        for path in RECIPES:
            r = json.loads(path.read_text("utf-8"))
            with self.subTest(slug=r["slug"]):
                self.assertEqual(self.errors(r), [])
                self.assertEqual(schema.check(r), [])

    def test_schema_catches_shape_problems(self):
        r = load()
        r["method"].append({"type": "stepp", "items": ["x"]})
        r["ingredientGroups"][0]["items"][0]["qty"] = 1
        errors = schema.check(r)
        self.assertTrue(any("method[" in e for e in errors))
        self.assertTrue(any("unknown field 'qty'" in e for e in errors))

    def test_ingredient_needs_a_scalable_quantity(self):
        r = load()
        r["ingredientGroups"][0]["items"].append({"name": "Paneer", "amount": "some"})
        self.assertTrue(any("no quantity to scale" in e for e in self.errors(r)))

    def test_onion_in_ingredients_is_an_error(self):
        r = load()
        r["ingredientGroups"][0]["items"].append({"name": "Red onion, chopped", "amount": "1"})
        self.assertTrue(any("onion" in e for e in self.errors(r)))

    def test_root_veg_only_in_toddler_portion(self):
        r = load()
        adult = copy.deepcopy(r)
        adult["ingredientGroups"][0]["items"].append({"name": "Potato, boiled", "amount": "1"})
        self.assertTrue(any("root vegetable" in e for e in self.errors(adult)))
        toddler = copy.deepcopy(r)
        toddler["ingredientGroups"].append({"label": "Toddler add-in", "items": [{"name": "Potato, boiled", "amount": "1"}]})
        self.assertEqual(self.errors(toddler), [])

    def test_substitution_notes_are_not_violations(self):
        r = load()
        r["method"][0]["items"].append("Hing {pinch} stands in — no onion or garlic needed")
        r["ingredientGroups"][0]["items"].append({"name": "Eggless wrappers", "amount": "4"})
        self.assertEqual(self.errors(r), [])

    def test_bad_slug(self):
        r = load()
        r["slug"] = "dinner-thing"
        self.assertTrue(self.errors(r))


class Tags(unittest.TestCase):
    def test_negated_appliance_is_not_tagged(self):
        r = load()
        r["method"][0]["items"].append("No air fryer needed here")
        self.assertNotIn("Air fryer", detect_tags(r))
        r["method"][0]["items"].append("Air-fry at 330°F for 6 min")
        self.assertIn("Air fryer", detect_tags(r))

    def test_only_vocabulary_tags(self):
        for path in RECIPES:
            r = json.loads(path.read_text("utf-8"))
            self.assertTrue(set(r["tags"]) <= set(TAG_NAMES), r["slug"])
            self.assertLessEqual(len(r["tags"]), 5, r["slug"])


class Scaling(unittest.TestCase):
    CASES = [
        ("1 cup", "2 cups"), ("⅓–½ cup", "⅔–1 cup"), ("1½ tbsp", "3 tbsp"), ("¾ tsp", "1½ tsp"),
        ("400g, cubed", "800g, cubed"), ("2–3 (1 milder)", "4–6 (1 milder)"), ("1 pinch", "2 pinches"),
        ("Makes 6–7 chillas", "Makes 12–14 chillas"), ("1 (adults only)", "2 (adults only)"),
        # fixed
        ("5 min", "5 min"), ("1 tsp per chilla", "1 tsp per chilla"), ("2 tbsp/roti", "2 tbsp/roti"),
        ("~2 tbsp each", "~2 tbsp each"), ("~1 inch layer", "~1 inch layer"), ("~6–7 in", "~6–7 in"),
        ("from Step 1", "from Step 1"), ("to taste", "to taste"), ("=1 cup", "1 cup"),
        ("Night prep: 5 min (soak)", "Night prep: 5 min (soak)"),
    ]

    def test_cases(self):
        for text, want in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(scale_text(text, 2), want)

    def test_one_x_reproduces_every_amount(self):
        # Formatting a parsed quantity must give back the exact original text,
        # otherwise the 1× view would differ from the recipe as written.
        for path in RECIPES:
            r = json.loads(path.read_text("utf-8"))
            texts = [i["amount"] for g in r["ingredientGroups"] for i in g["items"]] + r["meta"]
            for b in r["method"]:
                for item in b.get("items", []):
                    texts += [m for m in __import__("re").findall(r"\{([^}]*)\}", item)]
            for t in texts:
                with self.subTest(slug=r["slug"], amount=t):
                    self.assertEqual(scale_text(t, 1), t.lstrip("="))

    def test_every_ingredient_line_scales_or_says_why_not(self):
        for path in RECIPES:
            r = json.loads(path.read_text("utf-8"))
            for g in r["ingredientGroups"]:
                for i in g["items"]:
                    self.assertFalse(needs_quantity(i["amount"]), (r["slug"], i))

    def test_toddler_boxes_and_tips_never_get_scale_markers(self):
        page = render.recipe_page(load("rice-kashmiri-pulao"), CSS)
        toddler = page[page.index('class="toddler-box"'):]
        toddler = toddler[:toddler.index("</div>\n      <div")]
        self.assertNotIn('class="q"', toddler)
        self.assertIn('class="q"', page)
        self.assertNotIn('class="q"', render.recipe_page(load(), CSS, standalone=True))


if __name__ == "__main__":
    unittest.main()
