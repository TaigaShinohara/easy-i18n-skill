#!/usr/bin/env python3
"""Convert central JSON catalogs to platform files.

Targets:
  android  Writes an Android res layout under the output directory:
           values/strings.xml for the source locale and
           values-<lang>[-r<REGION>]/strings.xml for the rest.
           Literal %, apostrophes and double quotes are escaped for
           aapt, {name} placeholders become %N$s, and a leading @ or ?
           is escaped. ICU plural/select strings cannot be expressed
           as a plain <string>, so they are reported as warnings and
           written verbatim for a hand conversion to <plurals>.
  chrome   Writes <out>/<locale_with_underscore>/messages.json in
           chrome.i18n shape. {name} placeholders become $NAME$ with a
           matching placeholders entry ($1, $2, ... in order of first
           appearance). ICU plural/select strings are warned about,
           because chrome.i18n has no plural support.

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
NAMED_RE = re.compile(r"\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:,[^{}]*)?\}")


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
    name = key.replace(".", "_").replace("-", "_").lower()
    return re.sub(r"[^a-z0-9_]", "_", name)


def android_folder(locale, source):
    if locale == source:
        return "values"
    parts = locale.replace("_", "-").split("-")
    if len(parts) >= 2 and len(parts[1]) in (2, 3):
        return f"values-{parts[0]}-r{parts[1].upper()}"
    return f"values-{parts[0]}"


def escape_android_literal(text):
    # Escape literal percent signs first: every % in the source is a
    # literal, because placeholders arrive as {name} and are inserted
    # after this step.
    text = text.replace("%", "%%")
    text = text.replace("'", "\\'")
    text = text.replace('"', '\\"')
    if text.startswith(("@", "?")):
        text = "\\" + text
    return text


def to_android(text, key, warnings, locale):
    if ICU_COMPLEX_RE.search(text):
        warnings.append(
            f"{locale}: {key} uses ICU plural/select. "
            "Written verbatim - convert it to a <plurals> entry by hand."
        )
        return text
    order = []
    for match in NAMED_RE.finditer(text):
        name = match.group(1)
        if name not in order:
            order.append(name)
    converted = escape_android_literal(text)

    def repl(match):
        name = match.group(1)
        return f"%{order.index(name) + 1}$s"

    return NAMED_RE.sub(repl, converted)


def convert_android(catalogs, source, out_dir):
    warnings = []
    root_out = Path(out_dir)
    for locale, entries in catalogs.items():
        folder = root_out / android_folder(locale, source)
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


def chrome_locale(locale):
    return locale.replace("-", "_")


def to_chrome(text, key, warnings, locale):
    if ICU_COMPLEX_RE.search(text):
        warnings.append(
            f"{locale}: {key} uses ICU plural/select. "
            "chrome.i18n has no plural support - split keys with Intl.PluralRules."
        )
        return {"message": text}
    order = []
    for match in NAMED_RE.finditer(text):
        name = match.group(1)
        if name not in order:
            order.append(name)
    if not order:
        return {"message": text}

    def repl(match):
        return "$" + match.group(1).upper() + "$"

    entry = {"message": NAMED_RE.sub(repl, text)}
    entry["placeholders"] = {
        name: {"content": f"${idx + 1}"} for idx, name in enumerate(order)
    }
    return entry


def convert_chrome(catalogs, source, out_dir):
    warnings = []
    root_out = Path(out_dir)
    for locale, entries in catalogs.items():
        folder = root_out / chrome_locale(locale)
        folder.mkdir(parents=True, exist_ok=True)
        messages = {}
        for key in sorted(entries):
            chrome_key = re.sub(
                r"[^A-Za-z0-9_]", "_", key.replace(".", "_")
            )
            messages[chrome_key] = to_chrome(entries[key], key, warnings, locale)
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
