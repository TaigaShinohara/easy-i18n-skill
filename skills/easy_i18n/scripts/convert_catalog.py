#!/usr/bin/env python3
"""Convert central JSON catalogs to platform files.

Supported targets:
  android  -> <out>/<locale>/strings.xml style files are NOT written;
              instead writes res layout: <out>/values/strings.xml for the
              default locale and <out>/values-<locale>/strings.xml for
              the rest. ICU plural strings are reported as warnings and
              written as plain strings with a TODO comment, because
              Android needs a hand-checked <plurals> entry.
  chrome   -> <out>/<locale>/messages.json in chrome.i18n shape.
              Dots in keys become underscores (Chrome message names).

Usage:
  python3 convert_catalog.py android messages/ android-res/
  python3 convert_catalog.py chrome  messages/ extension/_locales/
      [--source en]
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ICU_COMPLEX_RE = re.compile(r"\{\s*[A-Za-z_][A-Za-z0-9_]*\s*,\s*(plural|select|selectordinal)\b")
NAMED_RE = re.compile(r"\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:,[^}]*)?\}")


def flatten(obj, prefix=""):
    out = {}
    for key, value in obj.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, name))
        else:
            out[name] = str(value)
    return out


def load_catalogs(messages_dir, source):
    base = Path(messages_dir)
    catalogs = {}
    for path in sorted(base.glob("*.json")):
        catalogs[path.stem] = flatten(json.loads(path.read_text(encoding="utf-8")))
    if source not in catalogs:
        raise SystemExit(f"source locale {source} not found in {base}")
    return catalogs


def android_name(key):
    return key.replace(".", "_").replace("-", "_")


def to_android(text, key, warnings, locale):
    # Order placeholders by first appearance and rewrite {name} to %N$s.
    order = []
    for match in NAMED_RE.finditer(text):
        name = match.group(1)
        # Skip the inner braces of ICU blocks; they are warned about below.
        if name not in order:
            order.append(name)

    def repl(match):
        name = match.group(1)
        idx = order.index(name) + 1
        return f"%{idx}$s"

    converted = NAMED_RE.sub(repl, text)
    if ICU_COMPLEX_RE.search(text):
        warnings.append(
            f"{locale}: {key} uses ICU plural/select. "
            "Written as a plain string - convert it to a <plurals> entry by hand."
        )
        # Strip the ICU wrapper crudely is unsafe; keep text visible for review.
        converted = text
    return converted


def convert_android(catalogs, source, out_dir):
    warnings = []
    root_out = Path(out_dir)
    for locale, entries in catalogs.items():
        folder = root_out / ("values" if locale == source else f"values-{locale}")
        folder.mkdir(parents=True, exist_ok=True)
        resources = ET.Element("resources")
        for key in sorted(entries):
            el = ET.SubElement(resources, "string", {"name": android_name(key)})
            el.text = to_android(entries[key], key, warnings, locale)
        tree = ET.ElementTree(resources)
        ET.indent(tree, space="    ")
        tree.write(folder / "strings.xml", encoding="utf-8", xml_declaration=True)
        print(f"android: {folder / 'strings.xml'} ({len(entries)} strings)")
    return warnings


def convert_chrome(catalogs, source, out_dir):
    warnings = []
    root_out = Path(out_dir)
    for locale, entries in catalogs.items():
        folder = root_out / locale
        folder.mkdir(parents=True, exist_ok=True)
        messages = {}
        for key in sorted(entries):
            chrome_key = key.replace(".", "_").replace("-", "_")
            entry = {"message": entries[key]}
            if ICU_COMPLEX_RE.search(entries[key]):
                warnings.append(
                    f"{locale}: {key} uses ICU plural/select. "
                    "chrome.i18n has no plural support - split keys with Intl.PluralRules."
                )
            messages[chrome_key] = entry
        (folder / "messages.json").write_text(
            json.dumps(messages, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"chrome: {folder / 'messages.json'} ({len(entries)} messages)")
    return warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=["android", "chrome"])
    parser.add_argument("messages_dir")
    parser.add_argument("out_dir")
    parser.add_argument("--source", default="en")
    args = parser.parse_args()

    catalogs = load_catalogs(args.messages_dir, args.source)
    if args.target == "android":
        warnings = convert_android(catalogs, args.source, args.out_dir)
    else:
        warnings = convert_chrome(catalogs, args.source, args.out_dir)
    for line in warnings:
        print(f"WARN: {line}")
    print(f"Done: {len(catalogs)} locale(s), {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
