#!/usr/bin/env python3
"""
Fields — the hero headline.

    python3 tools/build-hero.py

Sets the headline in Heart of the Land outlines and writes it into
site/index.html between the headline markers.

Two lines, broken for shape rather than grammar: "A world of Fields" is the
longer phrase and sits on top, "in your bowl" hangs under it. Breaking after
"of" instead leaves a short stub over a long line, which reads as a mistake.

The face is unicase, so the casing here is immaterial -- it sets as capitals
either way. It is rendered to outlines rather than served; see
tools/scripttype.py for why.
"""

import pathlib
import re
import sys

try:
    import scripttype
except ImportError:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import scripttype

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "site/index.html"

START, END = "<!-- headline:start -->", "<!-- headline:end -->"
LINES = ["A world of Fields", "in your bowl"]
TRACKING = 0.015


def build():
    # Each line gets a wrapper. replace() emits a hidden <span> before the
    # drawing, so without one the two svgs are not adjacent siblings and
    # neither `+` spacing nor :nth-child staggering can reach the second line.
    return "\n".join(
        '<span class="hero__line">'
        + scripttype.replace(line, font_path=scripttype.HEART,
                             css_class="hero__headline-line", tracking=TRACKING)
        + "</span>"
        for line in LINES
    )


def main():
    block = build()
    s = INDEX.read_text(encoding="utf-8")
    assert s.count(START) == 1 and s.count(END) == 1, "headline markers missing"
    out, n = re.subn(re.escape(START) + r".*?" + re.escape(END),
                     lambda _: START + "\n" + block + "\n" + END, s, flags=re.S)
    assert n == 1 and block in out, "headline substitution did not apply"
    INDEX.write_text(out, encoding="utf-8")
    print(f"headline: {len(LINES)} lines, {len(block)/1024:.1f} KB")
    for line in LINES:
        print(f"  {line}")


if __name__ == "__main__":
    main()
