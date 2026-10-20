#!/usr/bin/env python3
"""
Fields — the hero headline and subhead.

    python3 tools/build-hero.py

Both are set in outlines and written into site/index.html between their
markers.

The headline mixes faces on one line: "DIFFERENT" in Heart of the Land, the
noun in Midstar. That cannot be two images placed side by side -- the faces
disagree about size (Midstar's cap is 1.31x Heart of the Land's at the same
em, its x-height 0.469em against HotL's 0.700em cap), so each line is drawn
as ONE svg with both faces on a shared baseline.

Two numbers do that:

  SCRIPT_SCALE  the Midstar run's size against the caps. At 1.0 the script
                towers; this is tuned by eye against rendered proofs.
  the shift     scaling happens about the BASELINE, so a larger script gains
                all its height upward and climbs out of the line. The shift
                puts its optical centre back on the caps' optical centre,
                which is why growing the script does not move it.

A block may ship one set of lines, or a wide and a narrow set the stylesheet
swaps; a set named "only" shows at every width. The real words appear once
per block as hidden text; the drawn sets are decorative.
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

CAPS_TRACK = 0.02          # Heart of the Land caps in the headline
LABEL_TRACK = 0.14         # the brand's label style, per the Fields guidelines
SCRIPT_SCALE = 1.16


def caps_centre():
    """Optical middle of the caps, in ems from the baseline."""
    return scripttype.centre_shift("DIFFERENT", scripttype.HEART, 1.0, 0.0, CAPS_TRACK)


def script(word):
    """A Midstar run sized and shifted to sit centred on the caps."""
    own = scripttype.centre_shift(word, scripttype.FONT, 1.0, 0.0)
    return (word, "FONT", 0.0, SCRIPT_SCALE, caps_centre() - SCRIPT_SCALE * own)


# Wide: caps and script share a line. Narrow: they stack, because a phone
# cannot hold "DIFFERENT Fields." at a useful size -- the pair is 9.8em and
# lands at 34px on a 375px screen, where the subhead starts to compete with
# it. Stacked, the widest line is 5.5em and the type sets at 59px.
HEADLINE_WIDE = [
    [("Different", "HEART", CAPS_TRACK, 1.0), script("Fields.")],
    [("Different", "HEART", CAPS_TRACK, 1.0), script("Flavors.")],
]

# Alone on a line there are no caps to sit against, so no shift: the script
# keeps its own baseline.
HEADLINE_NARROW = [
    [("Different", "HEART", CAPS_TRACK, 1.0)],
    [("Fields.", "FONT", 0.0, SCRIPT_SCALE)],
    [("Different", "HEART", CAPS_TRACK, 1.0)],
    [("Flavors.", "FONT", 0.0, SCRIPT_SCALE)],
]

BLOCKS = {
    "headline": {
        "markers": ("<!-- headline:start -->", "<!-- headline:end -->"),
        "phrase": "Different Fields. Different Flavors.",
        "cls": "hero__headline-line",
        "sets": {"wide": HEADLINE_WIDE, "narrow": HEADLINE_NARROW},
    },
    "subhead": {
        "markers": ("<!-- subhead:start -->", "<!-- subhead:end -->"),
        "phrase": "Bright. Crunchy. A little unexpected.",
        "cls": "hero__subhead-line",
        "sets": {
            "wide":   [[("Bright. Crunchy. A little unexpected.", "HEART", LABEL_TRACK, 1.0)]],
            "narrow": [[("Bright. Crunchy.", "HEART", LABEL_TRACK, 1.0)],
                       [("A little unexpected.", "HEART", LABEL_TRACK, 1.0)]],
        },
    },
}


def resolve(run):
    text, face, tracking, scale = run[:4]
    shift = run[4] if len(run) > 4 else 0.0
    return (text, getattr(scripttype, face), tracking, scale, shift)


def line_svg(runs, cls):
    return scripttype.render_runs([resolve(r) for r in runs], css_class=cls,
                                  gap=0.16, aria_hidden=True)


def line_set(name, lines, cls):
    """--maxsw is the widest line's width in ems. The stylesheet divides the
    available width by it, so every line in the set shares a font-size."""
    svgs = [line_svg(l, cls) for l in lines]
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
