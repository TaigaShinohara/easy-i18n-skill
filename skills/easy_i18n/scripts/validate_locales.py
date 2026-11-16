#!/usr/bin/env python3
"""Validate locale catalogs against the source catalog.

Checks, for the source catalog and every other locale file:
  - no value is empty or whitespace only (source included)
  - braces are balanced and ICU plural/select blocks contain `other`
  - the flattened key set matches the source exactly (missing / extra keys)
  - the placeholder set per key matches the source

Usage:
  python3 validate_locales.py [messages_dir] [--source en]

Exit code 0 when everything matches, 1 otherwise.
Catalogs are JSON files named <locale>.json with nested objects whose
leaves are strings. Keys are flattened with dots, e.g. cart.checkout_cta.
Note: a key written both as a flat dotted key and as a nested object
collides after flattening. Keep one style per catalog.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*[,}]")
PERCENT_RE = re.compile(r"%\d+\$[sdif]|%[sdif]")
ICU_TYPE_RE = re.compile(r"\{\s*[A-Za-z_][A-Za-z0-9_]*\s*,\s*(plural|select|selectordinal)\s*,")


def flatten(obj, prefix=""):
    out = {}
    for key, value in obj.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, name))
        elif isinstance(value, str):
            out[name] = value
        else:
            out[name] = str(value)
    return out


def placeholders(text):
    names = set(PLACEHOLDER_RE.findall(text))
    names.discard("plural")
    names.discard("select")
    names.discard("selectordinal")
    return names, set(PERCENT_RE.findall(text))


def icu_problems(text):
    """Return a list of structural problems in one message string."""
    problems = []
    depth = 0
    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                problems.append("unbalanced braces (extra closing brace)")
                return problems
    if depth != 0:
        problems.append("unbalanced braces (missing closing brace)")
    # Every plural/select block needs an `other` branch. This is a
    # heuristic scan: it checks the text after each ICU header up to the
    # end of the string, which is good enough to catch a dropped branch.
    for match in ICU_TYPE_RE.finditer(text):
        tail = text[match.end():]
        if not re.search(r"\bother\s*\{", tail):
            problems.append(f"ICU {match.group(1)} block has no 'other' branch")
    return problems


def check_own_values(locale, data, errors):
    for key, value in data.items():
        if not value.strip():
            errors.append(f"{locale}: empty value {key}")
        for problem in icu_problems(value):
            errors.append(f"{locale}: {problem} in {key}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("messages_dir", nargs="?", default="messages")
    parser.add_argument("--source", default="en")
    args = parser.parse_args()

    base = Path(args.messages_dir)
    source_file = base / f"{args.source}.json"
    if not source_file.exists():
        print(f"ERROR: source catalog not found: {source_file}")
        return 1

    source = flatten(json.loads(source_file.read_text(encoding="utf-8")))
    errors = []
    check_own_values(args.source, source, errors)

    files = sorted(base.glob("*.json"))
    if len(files) < 2:
        print(f"WARN: only {len(files)} catalog file(s) found in {base}")

    for path in files:
        locale = path.stem
        if locale == args.source:
            continue
        try:
            data = flatten(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{locale}: invalid JSON ({exc})")
            continue
        check_own_values(locale, data, errors)
        missing = sorted(set(source) - set(data))
        extra = sorted(set(data) - set(source))
        for key in missing:
            errors.append(f"{locale}: missing key {key}")
        for key in extra:
            errors.append(f"{locale}: extra key {key}")
        for key in sorted(set(source) & set(data)):
            s_names, s_pct = placeholders(source[key])
            t_names, t_pct = placeholders(data[key])
            if s_names != t_names:
                errors.append(
                    f"{locale}: placeholder mismatch {key}: "
                    f"source {sorted(s_names)} vs locale {sorted(t_names)}"
                )
            if s_pct != t_pct:
                errors.append(
                    f"{locale}: percent placeholder mismatch {key}: "
                    f"source {sorted(s_pct)} vs locale {sorted(t_pct)}"
                )

    if errors:
        print(f"FAILED: {len(errors)} problem(s)")
        for line in errors:
            print(f"  - {line}")
        return 1
    print(f"OK: {len(source)} keys consistent across {len(files)} catalog(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
