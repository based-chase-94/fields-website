#!/usr/bin/env python3
"""
Fields — the hero headline and subhead.

    python3 tools/build-hero.py

Both are set in Heart of the Land outlines and written into site/index.html
between their markers.

Each block ships two sets of lines and the stylesheet shows one, because the
type size is set by the LONGEST line and a phone is narrow:

  headline  wide "Every field / tastes different"   9.7em  -> 25px cap at 375
            narrow "Every field / tastes / different" 6.4em -> 37px cap
  subhead   wide "Bright. Crunchy. A little unexpected."  22.0em
            narrow "Bright. Crunchy." / "A little unexpected."  12.0em

The real words appear once per block, as hidden text on the heading and the
paragraph; the drawn sets are decorative. Emitting them with each set would
duplicate the phrase for crawlers and read it twice to a screen reader.

The face is unicase, so casing here is immaterial -- it sets as capitals
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

BLOCKS = {
    "headline": {
        "markers": ("<!-- headline:start -->", "<!-- headline:end -->"),
        "phrase": "Every field tastes different",
        "cls": "hero__headline-line",
        # Midstar, the script. Zero tracking: the letters are drawn to join,
        # and spacing them apart breaks the joins.
        "font": "FONT",
        "tracking": 0.0,
        "sets": {
            "wide":   ["Every field", "tastes different"],
            "narrow": ["Every field", "tastes", "different"],
        },
    },
    "subhead": {
        "markers": ("<!-- subhead:start -->", "<!-- subhead:end -->"),
        "phrase": "Bright. Crunchy. A little unexpected.",
        "cls": "hero__subhead-line",
        "font": "HEART",
        "tracking": 0.03,
        "sets": {
            "wide":   ["Bright. Crunchy. A little unexpected."],
            "narrow": ["Bright. Crunchy.", "A little unexpected."],
        },
    },
}


def line_svg(text, cls, tracking, font):
    return scripttype.render(text, font_path=getattr(scripttype, font), css_class=cls,
                             tracking=tracking, aria_hidden=True)


def ratio(text, cls, tracking, font):
    return float(re.search(r"--sw:([\d.]+)", line_svg(text, cls, tracking, font)).group(1))


def line_set(name, lines, cls, tracking, font):
    """--maxsw is the widest line's width in ems. The stylesheet divides the
    available width by it, so every line in the set shares a font-size and
    therefore a cap height. Sizing each line off its own width and capping
    with max-width makes the LONGEST line render smallest."""
    widest = max(ratio(l, cls, tracking, font) for l in lines)
    body = "\n".join(f'<span class="hero__line">{line_svg(l, cls, tracking, font)}</span>'
                     for l in lines)
    return (f'<span class="hero__lines hero__lines--{name}" '
            f'style="--maxsw:{widest:.4f}" aria-hidden="true">\n{body}\n</span>')


def build(b):
    return (f'<span class="vh">{b["phrase"]}</span>\n'
            + "\n".join(line_set(n, ls, b["cls"], b["tracking"], b["font"])
                        for n, ls in b["sets"].items()))


def main():
    s = INDEX.read_text(encoding="utf-8")
    for key, b in BLOCKS.items():
        start, end = b["markers"]
        assert s.count(start) == 1 and s.count(end) == 1, f"{key} markers missing"
        block = build(b)
        s, n = re.subn(re.escape(start) + r".*?" + re.escape(end),
                       lambda _: start + "\n" + block + "\n" + end, s, flags=re.S)
        assert n == 1 and block in s, f"{key} substitution did not apply"
        print(f"{key}: {len(block)/1024:.1f} KB")
        for name, lines in b["sets"].items():
            widest = max(ratio(l, b["cls"], b["tracking"], b["font"]) for l in lines)
            print(f"  {name:7} {len(lines)} line(s), widest {widest:5.2f}em  "
                  f"({' / '.join(lines)})")
    INDEX.write_text(s, encoding="utf-8")


if __name__ == "__main__":
    main()
