#!/usr/bin/env python3
"""dhanjas.com recipe tool.

  python3 tools/recipes.py ingest [FILES...]   v2 HTML or JSON from inbox/ -> data/recipes/, then build
  python3 tools/recipes.py build               data/recipes/*.json -> index.html + <slug>.html pages
  python3 tools/recipes.py validate [SLUGS...] check recipes against the household + template rules
  python3 tools/recipes.py retag               recompute auto-detected tags (keeps hand-added ones)
  python3 tools/recipes.py export SLUG... [--format html|json|jsonld|all] [--all]
                                               standalone v2 HTML (style inlined), house JSON or schema.org JSON-LD
  python3 tools/recipes.py scaled SLUG [2]     preview the recipe's amounts at 2× (or any factor)

Python 3.8+, standard library only.
"""

import argparse
import datetime
from html import unescape as html_unescape
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dhanjas import parse_html, render, site, validate  # noqa: E402
from dhanjas.model import detect_tags, retag  # noqa: E402
from dhanjas.portions import lower  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "recipes"
INBOX = ROOT / "inbox"
PAGES = ROOT                     # recipe pages sit at the site root: /<slug> serves <slug>.html
FEEDS = ROOT / "recipes"         # published data: recipes/<slug>.json and .jsonld
ASSETS = ROOT / "assets"
EXPORT = ROOT / "export"

SCHEMA_REF = "../../schema/recipe.schema.json"            # for editors, relative to data/recipes/
SCHEMA_URL = "https://recipes.dhanjas.com/schema/recipe.schema.json"

FIELD_ORDER = ["$schema", "format", "slug", "category", "title", "name", "subtitle", "badges", "labels", "meta", "protein",
               "nightPrep", "ingredientsTitle", "ingredientGroups", "methodTitle", "method", "tags", "added", "source"]


def load_all():
    out = []
    for p in sorted(DATA.glob("*.json")):
        r = json.loads(p.read_text("utf-8"))
        r.pop("$schema", None)
        out.append(r)
    return out


def dump(recipe, schema_ref):
    recipe = dict(recipe, **{"$schema": schema_ref})
    ordered = {k: recipe[k] for k in FIELD_ORDER if k in recipe}
    ordered.update({k: v for k, v in recipe.items() if k not in ordered})
    # One ingredient per line (portions included) keeps the files easy to read and diff.
    lines = {}
    for g in ordered.get("ingredientGroups", []):
        for i, it in enumerate(g.get("items", [])):
            token = "\u0000ING%d\u0000" % len(lines)
            lines[token] = json.dumps(it, ensure_ascii=False)
            g["items"][i] = token
    text = json.dumps(ordered, ensure_ascii=False, indent=2)
    for token, line in lines.items():
        text = text.replace(json.dumps(token), line)
    for g in ordered.get("ingredientGroups", []):          # put the items back
        g["items"] = [json.loads(lines[t]) for t in g["items"]]
    return text + "\n"


def save(recipe):
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / ("%s.json" % recipe["slug"])).write_text(dump(recipe, SCHEMA_REF), "utf-8")


def report(slug, errors, warnings, quiet=False):
    for msg in errors:
        print("  ✗ %s: %s" % (slug, msg))
    if not quiet:
        for msg in warnings:
            print("  · %s: %s" % (slug, msg))


def cmd_build(args):
    recipes = load_all()
    css = (ASSETS / "recipe.css").read_text("utf-8")
    FEEDS.mkdir(exist_ok=True)
    wanted = set()
    failed = False
    for r in recipes:
        errors, _ = validate.check(r)
        if errors:
            failed = True
            report(r["slug"], errors, [], quiet=True)
        for name, content in exports(r, css, published=True).items():
            path = (PAGES if name.endswith(".html") else FEEDS) / name
            wanted.add(path)
            path.write_text(content, "utf-8")
    # a page is ours if the generator stamped it; never touch other HTML at the root
    stale = [p for p in PAGES.glob("*.html") if render.GENERATOR in p.read_text("utf-8")[:2000]]
    stale += [p for ext in ("*.json", "*.jsonld") for p in FEEDS.glob(ext)]
    for path in stale:
        if path not in wanted:
            path.unlink()
            print("removed %s" % path.relative_to(ROOT))
    views = [lower(r, 1) for r in recipes]
    (ROOT / "index.html").write_text(site.index_page(views), "utf-8")
    (ASSETS / "recipes.json").write_text(site.search_index(views), "utf-8")
    print("built %d recipe pages + index.html" % len(recipes))
    return 1 if failed and args.strict else 0


def cmd_validate(args):
    recipes = load_all()
    if args.slugs:
        recipes = [r for r in recipes if r["slug"] in args.slugs]
    n_err = n_warn = 0
    for r in recipes:
        errors, warnings = validate.check(r)
        n_err += len(errors)
        n_warn += len(warnings)
        report(r["slug"], errors, warnings, quiet=args.errors_only)
    print("%d recipes · %d errors · %d warnings" % (len(recipes), n_err, n_warn))
    return 1 if n_err else 0


def cmd_ingest(args):
    files = [Path(f) for f in args.files] if args.files else sorted(
        p for p in INBOX.glob("*") if p.suffix.lower() in (".html", ".htm", ".json"))
    if not files:
        print("nothing to ingest — drop recipe .json (or older v2 .html) files into inbox/")
        return 0
    today = datetime.date.today().isoformat()
    ok, failed = 0, 0
    for path in files:
        try:
            if path.suffix.lower() == ".json":
                recipe = json.loads(path.read_text("utf-8"))
                recipe.pop("$schema", None)
                recipe.setdefault("slug", parse_html.slug_from_filename(path.stem))
                if "tags" not in recipe:
                    recipe["tags"] = detect_tags(recipe)
            else:
                recipe = parse_html.parse(path.read_text("utf-8"), parse_html.slug_from_filename(path.name))
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            print("✗ %s: %s" % (path.name, exc))
            failed += 1
            continue

        slug = recipe["slug"]
        existing = DATA / ("%s.json" % slug)
        if existing.exists() and not args.replace:
            print("✗ %s: %s already exists — rerun with --replace to overwrite it" % (path.name, existing.relative_to(ROOT)))
            failed += 1
            continue
        if existing.exists():
            old = json.loads(existing.read_text("utf-8"))
            recipe.setdefault("added", old.get("added"))
            recipe["tags"] = retag(recipe, old.get("tags", []))  # keeps hand-added tags
        recipe.setdefault("added", today)
        if args.added:
            recipe["added"] = args.added

        errors, warnings = validate.check(recipe)
        print("%s %s -> data/recipes/%s.json" % ("✗" if errors else "✓", path.name, slug))
        if recipe.get("format") != 3:
            print("  · %s: format 2 — new recipes should use format 3 (docs/RECIPE-SPEC.md) so portions "
                  "like the toddler's share and 'rest' are computed" % slug)
        report(slug, errors, warnings)
        if errors and not args.force:
            failed += 1
            continue
        save(recipe)
        ok += 1
        if not args.keep and INBOX in path.resolve().parents:
            path.unlink()

    print("ingested %d, failed %d" % (ok, failed))
    if ok:
        cmd_build(argparse.Namespace(strict=False))
    return 1 if failed else 0


def cmd_retag(args):
    for r in load_all():
        new = detect_tags(r) if args.reset else retag(r)
        if new != r.get("tags"):
            print("%s: %s -> %s" % (r["slug"], r.get("tags"), new))
            r["tags"] = new
            save(r)
    return cmd_build(argparse.Namespace(strict=False))


def exports(r, css, published=False, formats=("html", "json", "jsonld")):
    """Every format a recipe is available in, keyed by file name.
    published=True is the website copy (shared CSS, scale markers, nav);
    otherwise html is a standalone v2 file with the stylesheet inlined."""
    out = {}
    if "html" in formats:
        out["%s.html" % r["slug"]] = render.recipe_page(r, css, standalone=not published)
    if "json" in formats:
        out["%s.json" % r["slug"]] = dump(r, SCHEMA_URL)
    if "jsonld" in formats:
        out["%s.jsonld" % r["slug"]] = json.dumps(render.json_ld_data(r), ensure_ascii=False, indent=2) + "\n"
    return out


def cmd_export(args):
    css = (ASSETS / "recipe.css").read_text("utf-8")
    EXPORT.mkdir(exist_ok=True)
    recipes = {r["slug"]: r for r in load_all()}
    slugs = list(recipes) if args.all else args.slugs
    formats = ("html", "json", "jsonld") if args.format == "all" else (args.format,)
    for slug in slugs:
        if slug not in recipes:
            print("✗ no recipe %r" % slug)
            return 1
        for name, content in exports(recipes[slug], css, formats=formats).items():
            (EXPORT / name).write_text(content, "utf-8")
            print("wrote export/%s" % name)
    return 0


def cmd_scaled(args):
    """Print a recipe's scalable amounts at a factor — a preview, and the reference
    the browser check compares assets/scale.js against."""
    recipes = {r["slug"]: r for r in load_all()}
    page = render.recipe_page(recipes[args.slug], "")
    out = []
    for attrs, original in re.findall(r'<data class="q"([^>]*)>([^<]*)</data>', page):
        scaled = re.search(r'data-x%s="([^"]*)"' % args.factor, attrs)
        out.append({"original": html_unescape(original), "scaled": html_unescape(scaled.group(1)) if scaled else html_unescape(original)})
    print(json.dumps(out, ensure_ascii=False, indent=1 if args.pretty else None))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("build", help="regenerate the site")
    p.add_argument("--strict", action="store_true", help="exit non-zero if any recipe has validation errors")
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser("validate", help="check recipes")
    p.add_argument("slugs", nargs="*")
    p.add_argument("--errors-only", action="store_true")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("ingest", help="import recipes from inbox/ (or the given files)")
    p.add_argument("files", nargs="*")
    p.add_argument("--replace", action="store_true", help="overwrite an existing recipe with the same slug")
    p.add_argument("--force", action="store_true", help="save even if validation reports errors")
    p.add_argument("--keep", action="store_true", help="leave the source file in inbox/")
    p.add_argument("--added", help="override the 'added' date (YYYY-MM-DD)")
    p.set_defaults(fn=cmd_ingest)

    p = sub.add_parser("retag", help="recompute auto-detected tags (hand-added tags are kept)")
    p.add_argument("--reset", action="store_true", help="drop hand-added tags too")
    p.set_defaults(fn=cmd_retag)

    p = sub.add_parser("export", help="write recipes to export/ as standalone v2 HTML, house JSON or schema.org JSON-LD")
    p.add_argument("slugs", nargs="*")
    p.add_argument("--all", action="store_true", help="every recipe")
    p.add_argument("--format", choices=("html", "json", "jsonld", "all"), default="html")
    p.set_defaults(fn=cmd_export)

    p = sub.add_parser("scaled", help="show a recipe's scalable amounts at a factor, e.g. scaled dal-urad-makhani 2")
    p.add_argument("slug")
    p.add_argument("factor", nargs="?", default="2", choices=("2", "3"))
    p.add_argument("--pretty", action="store_true")
    p.set_defaults(fn=cmd_scaled)

    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
