#!/usr/bin/env python3
"""
Fields — the hero headline and subhead.

    python3 tools/build-hero.py

Both are set in outlines and written into site/index.html between their
markers. The faces are swapped against the brand's usual pairing: Heart of
the Land carries the headline, Midstar the line beneath it.

Each block ships a wide and a narrow set of lines and the stylesheet shows
one, because the type size is set by the LONGEST line and a phone is narrow.
On one line at 375px the headline falls to a 26px cap and the script's
x-height to 10.7px, which is not a reading size:

  headline  wide   "Find your field"                        9.0em
            narrow "Find your" / "field"                    5.7em  (cap 42px)
  subhead   wide   "Bright. Crunchy. A little unexpected."  14.4em
            narrow "Bright. Crunchy." / "A little unexpected."  7.0em

The two faces are not comparable at a shared font-size. Heart of the Land is
all caps at 0.725em; Midstar's x-height is 0.469em and its box runs to
1.141em on ascenders and descenders. So the subhead's size cap in the
stylesheet is set for the script, not carried over from when that slot held
Heart of the Land.

The real words appear once per block as hidden text; the drawn sets are
decorative. The face is licensed and rendered to outlines rather than served
-- see tools/scripttype.py.
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

HEAD_TRACK = 0.04     # Heart of the Land, display size
SUB_TRACK = 0.0       # Midstar joins; tracking breaks the joins

BLOCKS = {
    "headline": {
        "markers": ("<!-- headline:start -->", "<!-- headline:end -->"),
        "phrase": "Find your field",
        "cls": "hero__headline-line",
        "sets": {
            "wide":   [[("Find your field", "HEART", HEAD_TRACK, 1.0)]],
            "narrow": [[("Find your", "HEART", HEAD_TRACK, 1.0)],
                       [("field", "HEART", HEAD_TRACK, 1.0)]],
        },
    },
    "subhead": {
        "markers": ("<!-- subhead:start -->", "<!-- subhead:end -->"),
        "phrase": "Bright. Crunchy. A little unexpected.",
        "cls": "hero__subhead-line",
        "sets": {
            "wide":   [[("Bright. Crunchy. A little unexpected.", "FONT", SUB_TRACK, 1.0)]],
            "narrow": [[("Bright. Crunchy.", "FONT", SUB_TRACK, 1.0)],
                       [("A little unexpected.", "FONT", SUB_TRACK, 1.0)]],
        },
    },
}


def resolve(run):
    text, face, tracking, scale = run[:4]
    shift = run[4] if len(run) > 4 else 0.0
    return (text, getattr(scripttype, face), tracking, scale, shift)


def line_set(name, lines, cls):
    """--maxsw is the widest line's width in ems. The stylesheet divides the
    available width by it, so every line in the set shares a font-size and
    therefore a cap height. Sizing each line off its own width and capping
    with max-width makes the LONGEST line render smallest."""
    svgs = [scripttype.render_runs([resolve(r) for r in l], css_class=cls,
                                   gap=0.16, aria_hidden=True) for l in lines]
    widest = max(float(re.search(r"--sw:([\d.]+)", s).group(1)) for s in svgs)
    body = "\n".join(f'<span class="hero__line">{s}</span>' for s in svgs)
    return (f'<span class="hero__lines hero__lines--{name}" '
            f'style="--maxsw:{widest:.4f}" aria-hidden="true">\n{body}\n</span>'), widest


def main():
    s = INDEX.read_text(encoding="utf-8")
    for key, b in BLOCKS.items():
        start, end = b["markers"]
        assert s.count(start) == 1 and s.count(end) == 1, f"{key} markers missing"
        parts, widths = [], {}
        for name, lines in b["sets"].items():
            block, widest = line_set(name, lines, b["cls"])
            parts.append(block)
            widths[name] = widest
        block = f'<span class="vh">{b["phrase"]}</span>\n' + "\n".join(parts)
        s, n = re.subn(re.escape(start) + r".*?" + re.escape(end),
                       lambda _: start + "\n" + block + "\n" + end, s, flags=re.S)
        assert n == 1 and block in s, f"{key} substitution did not apply"
        print(f"{key}: {len(block)/1024:.1f} KB")
        for name, w in widths.items():
            print(f"  {name:7} widest {w:5.2f}em")
    INDEX.write_text(s, encoding="utf-8")


if __name__ == "__main__":
    main()
