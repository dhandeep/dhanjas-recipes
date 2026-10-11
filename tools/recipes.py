#!/usr/bin/env python3
"""dhanjas.com recipe tool.

  python3 tools/recipes.py ingest [FILES...]   v2 HTML or JSON from inbox/ -> data/recipes/, then build
  python3 tools/recipes.py build               data/recipes/*.json -> index.html + recipes/*.html
  python3 tools/recipes.py validate [SLUGS...] check recipes against the household + template rules
  python3 tools/recipes.py retag               recompute auto-detected tags (keeps hand-added ones)
  python3 tools/recipes.py export SLUG...      write self-contained v2 HTML (style inlined) to export/

Python 3.8+, standard library only.
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dhanjas import parse_html, render, site, validate  # noqa: E402
from dhanjas.model import detect_tags, retag  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "recipes"
INBOX = ROOT / "inbox"
PAGES = ROOT / "recipes"
ASSETS = ROOT / "assets"
EXPORT = ROOT / "export"

FIELD_ORDER = ["slug", "category", "title", "name", "subtitle", "badges", "labels", "meta", "protein",
               "nightPrep", "ingredientsTitle", "ingredientGroups", "methodTitle", "method", "tags", "added", "source"]


def load_all():
    return [json.loads(p.read_text("utf-8")) for p in sorted(DATA.glob("*.json"))]


def save(recipe):
    ordered = {k: recipe[k] for k in FIELD_ORDER if k in recipe}
    ordered.update({k: v for k, v in recipe.items() if k not in ordered})
    text = json.dumps(ordered, ensure_ascii=False, indent=2)
    # One ingredient per line keeps the files easy to read and diff.
    text = re.sub(r'\{\n\s+("name": .*?),\n\s+("amount": .*?)\n\s+\}', r"{\1, \2}", text)
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / ("%s.json" % recipe["slug"])).write_text(text + "\n", "utf-8")


def report(slug, errors, warnings, quiet=False):
    for msg in errors:
        print("  ✗ %s: %s" % (slug, msg))
    if not quiet:
        for msg in warnings:
            print("  · %s: %s" % (slug, msg))


def cmd_build(args):
    recipes = load_all()
    css = (ASSETS / "recipe.css").read_text("utf-8")
    PAGES.mkdir(exist_ok=True)
    wanted = set()
    failed = False
    for r in recipes:
        errors, _ = validate.check(r)
        if errors:
            failed = True
            report(r["slug"], errors, [], quiet=True)
        out = PAGES / ("%s.html" % r["slug"])
        wanted.add(out.name)
        out.write_text(render.recipe_page(r, css), "utf-8")
    for stale in PAGES.glob("*.html"):
        if stale.name not in wanted:
            stale.unlink()
            print("removed %s" % stale.relative_to(ROOT))
    (ROOT / "index.html").write_text(site.index_page(recipes), "utf-8")
    (ASSETS / "recipes.json").write_text(site.search_index(recipes), "utf-8")
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
        print("nothing to ingest — drop v2 .html or .json recipe files into inbox/")
        return 0
    today = datetime.date.today().isoformat()
    ok, failed = 0, 0
    for path in files:
        try:
            if path.suffix.lower() == ".json":
                recipe = json.loads(path.read_text("utf-8"))
                recipe.setdefault("slug", parse_html.slug_from_filename(path.stem))
                recipe.setdefault("category", recipe["slug"].split("-", 1)[0])
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
        new = retag(r)
        if new != r.get("tags"):
            print("%s: %s -> %s" % (r["slug"], r.get("tags"), new))
            r["tags"] = new
            save(r)
    return cmd_build(argparse.Namespace(strict=False))


def cmd_export(args):
    css = (ASSETS / "recipe.css").read_text("utf-8")
    EXPORT.mkdir(exist_ok=True)
    recipes = {r["slug"]: r for r in load_all()}
    for slug in args.slugs:
        if slug not in recipes:
            print("✗ no recipe %r" % slug)
            return 1
        out = EXPORT / ("%s.html" % slug)
        out.write_text(render.recipe_page(recipes[slug], css, standalone=True), "utf-8")
        print("wrote %s" % out.relative_to(ROOT))
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
    p.set_defaults(fn=cmd_retag)

    p = sub.add_parser("export", help="write standalone v2 HTML files to export/")
    p.add_argument("slugs", nargs="+")
    p.set_defaults(fn=cmd_export)

    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
