"""Parse a v2 recipe HTML file (the self-contained format from RECIPE-HTML-SPEC.md)
into the JSON model. Only class names matter; the <style> block is ignored."""

import re
from html.parser import HTMLParser

from .model import CATEGORIES, detect_tags

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []  # Node or str

    @property
    def classes(self):
        return (self.attrs.get("class") or "").split()

    def has(self, cls):
        return cls in self.classes

    def elements(self):
        return [c for c in self.children if isinstance(c, Node)]

    def find_all(self, cls=None, tag=None):
        out = []
        for c in self.elements():
            if (cls is None or c.has(cls)) and (tag is None or c.tag == tag):
                out.append(c)
            out += c.find_all(cls, tag)
        return out

    def find(self, cls=None, tag=None):
        found = self.find_all(cls, tag)
        return found[0] if found else None

    def text(self):
        return squash("".join(c if isinstance(c, str) else c.text() for c in self.children))


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.cur = Node("#root", [])

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        node = self.cur
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.cur = node.parent

    def handle_data(self, data):
        if self.cur.tag not in ("style", "script"):
            self.cur.children.append(data)


def squash(s):
    return re.sub(r"\s+", " ", s).strip()


def strip_icon(s):
    """Drop a leading emoji (or its mojibake) from box labels; the builder re-adds it."""
    return re.sub(r"^[^\w(]+", "", s).strip()


def inline(node):
    """Element content -> inline markup ({amount}, **bold**)."""
    out = []
    for c in node.children:
        if isinstance(c, str):
            out.append(c)
        elif c.has("amt"):
            t = c.text()
            if t.startswith("(") and t.endswith(")"):
                t = t[1:-1]
            out.append("{%s%s}" % ("=" if "data-fixed" in c.attrs else "", t.strip()))
        elif c.tag in ("strong", "b"):
            out.append("**%s**" % inline(c))
        elif c.tag == "br":
            out.append(" ")
        else:
            out.append(inline(c))
    return squash("".join(out))


def items(node):
    ul = node.find(tag="ul")
    return [inline(li) for li in ul.elements() if li.tag == "li"] if ul else []


def parse(html, slug):
    tb = TreeBuilder()
    tb.feed(html)
    root = tb.root

    header = root.find("site-header")
    section = root.find("recipe")
    if section is None:
        raise ValueError("no <section class=\"recipe\"> found — is this a v2 recipe file?")
    if len(root.find_all("recipe")) > 1:
        raise ValueError("file contains more than one recipe — the spec allows one recipe per file")

    name = section.find("recipe-name")
    h1 = header.find(tag="h1") if header else None
    subtitle = header.find("subtitle") if header else None
    title = (h1 or name).text()

    recipe = {
        "slug": slug,
        "category": slug.split("-", 1)[0],
        "title": title,
        "subtitle": subtitle.text() if subtitle else "",
        "badges": [b.text() for b in header.find_all("badge")] if header else [],
        "labels": [t.text() for t in section.find_all("recipe-tag")],
        "meta": [],
        "protein": None,
        "nightPrep": None,
        "ingredientGroups": [],
        "method": [],
    }
    if name is not None and name.text() != title:
        recipe["name"] = name.text()

    meta = section.find("recipe-meta")
    if meta:
        for span in meta.elements():
            span.children = [c for c in span.children if not (isinstance(c, Node) and c.has("dot"))]
            recipe["meta"].append(span.text())

    protein = section.find("protein-bar")
    if protein:
        recipe["protein"] = protein.text()

    night = section.find("night-prep")
    if night:
        label = night.find("night-label")
        recipe["nightPrep"] = {"label": strip_icon(label.text()) if label else "Night Before", "items": items(night)}

    for block, key, default in (("ingredients-block", "ingredientsTitle", "Ingredients"), ("steps-block", "methodTitle", "Method")):
        el = section.find(block)
        title = el.find("section-title") if el else None
        if title is not None and title.text() != default:
            recipe[key] = title.text()

    for group in section.find_all("ingredient-group"):
        label = group.find("ingredient-group-label")
        rows = []
        for li in group.find_all(tag="li"):
            n, a = li.find("ing-name"), li.find("ing-amount")
            rows.append({"name": inline(n) if n else inline(li), "amount": a.text() if a else ""})
        recipe["ingredientGroups"].append({"label": label.text() if label else "", "items": rows})

    steps = section.find("steps-block")
    for block in (steps.elements() if steps else []):
        if block.has("step"):
            title_el = block.find("step-title")
            if title_el:
                num = title_el.find("step-num")
                if num in title_el.children:
                    title_el.children.remove(num)
            recipe["method"].append({"type": "step", "title": title_el.text() if title_el else "", "items": items(block)})
            for nested in block.find_all("toddler-box"):  # tolerate a toddler box nested in a step
                recipe["method"].append(toddler(nested))
        elif block.has("toddler-box"):
            recipe["method"].append(toddler(block))
        elif block.has("tip-box"):
            strong = block.find(tag="strong")
            label = strong.text() if strong else "Tip"
            if strong in block.children:
                block.children.remove(strong)
            recipe["method"].append({"type": "tip", "label": label, "text": inline(block)})

    recipe["tags"] = detect_tags(recipe)
    return recipe


def toddler(box):
    label = box.find("toddler-label")
    return {"type": "toddler", "label": strip_icon(label.text()) if label else "Toddler", "items": items(box)}


def slug_from_filename(filename):
    base = re.sub(r"\.html?$", "", filename.rsplit("/", 1)[-1], flags=re.I)
    base = re.sub(r"\s*\(\d+\)$", "", base)  # Drive duplicate suffix: "name (1).html"
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")


def known_category(slug):
    return slug.split("-", 1)[0] in CATEGORIES
