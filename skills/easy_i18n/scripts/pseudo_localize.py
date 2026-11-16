#!/usr/bin/env python3
"""Generate a pseudo-localized catalog from the source catalog.

Pseudo-localization accents vowels, wraps each string in brackets and
expands it by roughly 30 to 40 percent. Run the app in this locale before
any real translation to expose hardcoded strings, truncation and encoding
problems.

Usage:
  python3 pseudo_localize.py messages/en.json messages/en-XA.json
"""
import json
import sys
from pathlib import Path

ACCENT = str.maketrans({
    "a": "à", "e": "ē", "i": "ï", "o": "ō", "u": "ū",
    "A": "À", "E": "Ē", "I": "Ï", "O": "Ō", "U": "Ū",
    "c": "ç", "n": "ñ", "s": "š", "y": "ÿ",
    "C": "Ç", "N": "Ñ", "S": "Š", "Y": "Ÿ",
})


def pseudo(text):
    # Keep placeholders untouched: split on { ... } spans (one level is
    # enough for a layout smoke test; ICU nesting is preserved as-is
    # because braces are copied verbatim).
    out = []
    depth = 0
    buf = ""
    for ch in text:
        if ch == "{":
            if depth == 0 and buf:
                out.append(buf.translate(ACCENT))
                buf = ""
            depth += 1
            out.append(ch)
        elif ch == "}":
            depth -= 1
            out.append(ch)
        elif depth == 0:
            buf += ch
        else:
            out.append(ch)
    if buf:
        out.append(buf.translate(ACCENT))
    body = "".join(out)
    pad_len = max(1, int(len(text) * 0.35))
    return "[" + body + " " + "·" * 0 + "ē" * pad_len + "]"


def walk(obj):
    if isinstance(obj, dict):
        return {k: walk(v) for k, v in obj.items()}
    if isinstance(obj, str):
        return pseudo(obj)
    return obj


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    data = json.loads(src.read_text(encoding="utf-8"))
    dst.write_text(
        json.dumps(walk(data), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote pseudo locale: {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
