"""python3 -m unittest discover -s tools"""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dhanjas import parse_html, render, validate  # noqa: E402
from dhanjas.model import detect_tags, filter_tags  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RECIPES = sorted((ROOT / "data" / "recipes").glob("*.json"))
CSS = (ROOT / "assets" / "recipe.css").read_text("utf-8")


def load(name="breakfast-moong-dal-chilla"):
    return json.loads((ROOT / "data" / "recipes" / ("%s.json" % name)).read_text("utf-8"))


class RoundTrip(unittest.TestCase):
    def test_every_recipe_survives_render_and_parse(self):
        self.assertTrue(RECIPES)
        for path in RECIPES:
            want = json.loads(path.read_text("utf-8"))
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
        self.assertEqual(render.rich("Add salt {½ tsp} & **stir**"),
                         'Add salt <span class="amt">(½ tsp)</span> &amp; <strong>stir</strong>')


class Validator(unittest.TestCase):
    def errors(self, recipe):
        return validate.check(recipe)[0]

    def test_all_recipes_pass(self):
        for path in RECIPES:
            r = json.loads(path.read_text("utf-8"))
            with self.subTest(slug=r["slug"]):
                self.assertEqual(self.errors(r), [])

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

    def test_label_pills_split_into_filters(self):
        r = {"labels": ["Quinoa · High protein"], "tags": ["High-protein", "Night prep"]}
        self.assertEqual(filter_tags(r), ["Quinoa", "High-protein", "Night prep"])


if __name__ == "__main__":
    unittest.main()
