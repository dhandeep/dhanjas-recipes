"""Checks a recipe against schema/recipe.schema.json.

A deliberately small JSON Schema validator — just the keywords the recipe schema
uses — so the tooling stays dependency-free. Any standard validator (ajv,
python-jsonschema, VS Code) gives the same answers on the same file.
"""

import json
import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "recipe.schema.json"
TYPES = {"object": dict, "array": list, "string": str, "null": type(None), "integer": int, "number": (int, float), "boolean": bool}


def load():
    return json.loads(SCHEMA_PATH.read_text("utf-8"))


def _check(value, schema, path, errors):
    if "oneOf" in schema:
        results = []
        for option in schema["oneOf"]:
            errs = []
            _check(value, option, path, errs)
            results.append(errs)
        ok = [r for r in results if not r]
        if len(ok) != 1:
            # Report the closest option's errors (fewest problems).
            errors.extend(min(results, key=len) if not ok else ["%s matches more than one option" % path])
        return
    if "const" in schema and value != schema["const"]:
        errors.append("%s must be %r" % (path, schema["const"]))
    if "enum" in schema and value not in schema["enum"]:
        errors.append("%s: %r is not one of %s" % (path, value, ", ".join(map(str, schema["enum"]))))
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(isinstance(value, TYPES[t]) and not (t in ("integer", "number") and isinstance(value, bool)) for t in types):
            errors.append("%s should be %s" % (path, " or ".join(types)))
            return
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append("%s is empty" % path)
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append("%s: %r doesn't match %s" % (path, value, schema["pattern"]))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append("%s needs at least %d item(s)" % (path, schema["minItems"]))
        if schema.get("uniqueItems") and len(set(map(json.dumps, value))) != len(value):
            errors.append("%s has duplicates" % path)
        for i, item in enumerate(value):
            if "items" in schema:
                _check(item, schema["items"], "%s[%d]" % (path, i), errors)
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append("%s is missing %r" % (path, key))
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties")
        if len(value) < schema.get("minProperties", 0):
            errors.append("%s needs at least %d entries" % (path, schema["minProperties"]))
        for key, item in value.items():
            if "propertyNames" in schema:
                _check(key, schema["propertyNames"], "%s key %r" % (path, key), errors)
            if key in props:
                _check(item, props[key], "%s.%s" % (path, key), errors)
            elif extra is False:
                errors.append("%s has unknown field %r" % (path, key))
            elif isinstance(extra, dict):
                _check(item, extra, "%s.%s" % (path, key), errors)


def check(recipe, schema=None):
    errors = []
    _check(recipe, schema or load(), "recipe", errors)
    return errors
