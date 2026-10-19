#!/usr/bin/env python3
"""
Fields — set a short string in Midstar and return it as SVG outlines.

Midstar is licensed from Subectype. The font's own metadata says:

    "You can not resell, share or giveaway the font files"

Serving a webfont hands the file to every visitor, and this repo is public,
so the file cannot ship either way. Outlines are the way the wordmark already
works: the shapes travel, the font does not. Keep source/fonts/ gitignored.

Build-time only. Needs fonttools and uharfbuzz:

    python3 -m pip install --user fonttools uharfbuzz

Text is shaped with HarfBuzz rather than by stacking advance widths. Midstar
carries a `kern` feature and `liga` substitutions; naive stacking happens to
match for today's headings but silently breaks on the first string where it
doesn't.
"""

import functools
import pathlib

from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
import uharfbuzz as hb

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Both are licensed and both are rendered to outlines rather than served.
# Midstar's own metadata forbids sharing the file outright; Heart of the Land
# carries no embedded terms either way, and nobody has the purchase record, so
# it gets the same treatment. Absence of a prohibition is not a grant.
FONT = ROOT / "source/fonts/Midstar.otf"                      # script, menu titles
HEART = ROOT / "source/fonts/Heart-of-the-Land-Regular.otf"   # unicase, display


class FontMissing(Exception):
    pass


@functools.lru_cache(maxsize=None)
def _load(path):
    p = pathlib.Path(path)
    if not p.exists():
        raise FontMissing(
            f"{p} not found.\n"
            "Midstar is licensed and deliberately untracked. Copy it from the\n"
            "style guide into source/fonts/ — it stays gitignored."
        )
    tt = TTFont(p)
    blob = hb.Blob.from_file_path(str(p))
    return tt, tt.getGlyphSet(), tt["head"].unitsPerEm, hb.Font(hb.Face(blob))


def _shape(hbfont, text):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf)
    return list(zip(buf.glyph_infos, buf.glyph_positions))


def render(text, font_path=FONT, css_class="scripttype", label=None):
    """Return an <svg> whose paths are `text` set in Midstar.

    The svg is sized in em, so it scales with the font-size of whatever
    contains it, exactly as live text would.
    """
    tt, glyphs, upm, hbfont = _load(str(font_path))
    order = tt.getGlyphOrder()

    paths, pen_x = [], 0
    bounds = BoundsPen(glyphs)

    for info, pos in _shape(hbfont, text):
        name = order[info.codepoint]          # codepoint is a glyph id after shaping
        # Flip y into SVG space and place the glyph at the pen.
        tf = Transform(1, 0, 0, -1, pen_x + pos.x_offset, -pos.y_offset)
        spen = SVGPathPen(glyphs)
        glyphs[name].draw(TransformPen(spen, tf))
        d = spen.getCommands()
        if d:
            paths.append(d)
        glyphs[name].draw(TransformPen(bounds, tf))
        pen_x += pos.x_advance

    if bounds.bounds is None:
        raise ValueError(f"{text!r} produced no outlines")

    x0, y0, x1, y1 = bounds.bounds
    w, h = x1 - x0, y1 - y0

    return (
        f'<svg class="{css_class}" role="img" aria-label="{label or text}" '
        f'viewBox="{x0:.0f} {y0:.0f} {w:.0f} {h:.0f}" '
        f'style="width:{w / upm:.4f}em;height:{h / upm:.4f}em" '
        f'preserveAspectRatio="xMinYMid meet" fill="currentColor">'
        f'<path d="{"".join(paths)}"/></svg>'
    )


if __name__ == "__main__":
    import sys
    for t in sys.argv[1:] or ["House Bowls", "Build Your Own"]:
        s = render(t)
        print(f"{t!r}: {len(s)} chars, {s[s.index('style=')+7:s.index('em;')+2]}")
