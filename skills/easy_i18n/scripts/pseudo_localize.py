#!/usr/bin/env python3
"""Generate a pseudo-localized catalog from the source catalog.

Pseudo-localization accents vowels, wraps each string in brackets and
expands it by roughly 30 to 40 percent. Run the app in this locale before
any real translation to expose hardcoded strings, truncation and encoding
problems.

ICU-aware: literal text inside plural/select branches is accented too,
while variable names, ICU keywords and selectors are copied verbatim, so
the pseudo catalog still parses as valid ICU. For messages that contain
an ICU block, the expansion padding lands as trailing literal text after
the block. That is deliberate for a layout smoke test: it stays visible
in every branch and makes overflow easy to spot.

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

ICU_BRANCH_TYPES = {"plural", "select", "selectordinal"}


def accent(text):
    return text.translate(ACCENT)


def parse_message(s, i, nested):
    """Accent literal text from index i. Returns (text, next_i).

    When nested is True, stops after the matching closing brace.
    Argument headers and selectors are copied verbatim.
    """
    out = []
    buf = []
    n = len(s)

    def flush():
        if buf:
            out.append(accent("".join(buf)))
            buf.clear()

    while i < n:
        ch = s[i]
        if ch == "{":
            flush()
            arg, i = parse_arg(s, i)
            out.append(arg)
        elif ch == "}":
            if nested:
                flush()
                return "".join(out), i + 1
            buf.append(ch)
            i += 1
        else:
            buf.append(ch)
            i += 1
    flush()
    return "".join(out), i


def parse_arg(s, i):
    """Parse one { ... } argument starting at s[i] == '{'. Verbatim
    header, accented branch bodies for plural/select types."""
    n = len(s)
    out = ["{"]
    i += 1
    # Variable name and optional type: copy until ',' or '}' or '{'.
    header = []
    arg_type = None
    parts = 0
    while i < n:
        ch = s[i]
        if ch == ",":
            parts += 1
            header.append(ch)
            i += 1
        elif ch == "}":
            out.append("".join(header))
            out.append("}")
            return "".join(out), i + 1
        elif ch == "{":
            # Start of the first branch body in a plural/select style.
            break
        else:
            header.append(ch)
            i += 1
            if parts == 1:
                word = "".join(header).split(",")[-1].strip()
                if word:
                    arg_type = word
    out.append("".join(header))
    if arg_type not in ICU_BRANCH_TYPES:
        # Format pattern (number/date/time style) or malformed input:
        # copy verbatim up to the matching closing brace.
        depth = 1
        while i < n and depth:
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            out.append(s[i])
            i += 1
        out.append("}")
        return "".join(out), i
    # Style: repeated `selector { body }` chunks, then the closing brace.
    while i < n:
        # Selector: copy spaces and the selector token verbatim.
        while i < n and s[i] not in "{}":
            out.append(s[i])
            i += 1
        if i < n and s[i] == "{":
            out.append("{")
            body, i = parse_message(s, i + 1, nested=True)
            out.append(body)
            out.append("}")
        elif i < n and s[i] == "}":
            out.append("}")
            return "".join(out), i + 1
    return "".join(out), i


def pseudo(text):
    body, _ = parse_message(text, 0, nested=False)
    pad_len = max(1, int(len(text) * 0.35))
    return "[" + body + " " + "ē" * pad_len + "]"


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
