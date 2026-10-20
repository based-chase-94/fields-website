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


def render(text, font_path=FONT, css_class="scripttype", label=None,
           tracking=0.0, aria_hidden=False):
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
        # CSS letter-spacing cannot reach outlines — it has to be baked in.
        pen_x += pos.x_advance + tracking * upm

    if bounds.bounds is None:
        raise ValueError(f"{text!r} produced no outlines")

    x0, y0, x1, y1 = bounds.bounds
    w, h = x1 - x0, y1 - y0

    a11y = ('aria-hidden="true"' if aria_hidden
            else f'role="img" aria-label="{html.escape(label or text, quote=True)}"')
    return (
        # Size as unitless ratios, not a fixed width: an inline width cannot
        # be overridden by CSS, so the drawing could not shrink inside a flex
        # row and pushed the layout wider than the viewport. The stylesheet
        # turns these into width/aspect-ratio and can cap them.
        f'<svg class="{css_class}" {a11y} '
        f'viewBox="{x0:.0f} {y0:.0f} {w:.0f} {h:.0f}" '
        f'style="--sw:{w / upm:.4f};--sh:{h / upm:.4f}" '
        f'preserveAspectRatio="xMinYMid meet" fill="currentColor">'
        f'<path d="{"".join(paths)}"/></svg>'
    )


def render_runs(runs, css_class="scripttype", label=None, gap=0.0,
                aria_hidden=False):
    """One line, several faces, one baseline.

    `runs` is a list of (text, font_path, tracking, scale) or
    (text, font_path, tracking, scale, shift). Every run is drawn against the
    same baseline at y=0 and the pen carries across them, so the faces sit on
    a shared line instead of being stacked images nudged into place by eye.

    `shift` moves a run off that baseline, in ems, positive downward. Growing
    a run by scale alone grows it about the baseline, so a script gains all
    its new height upward and appears to climb out of the line; a shift of
    `centre_shift()` holds its optical centre where it was.

    `scale` exists because the faces disagree about size: Midstar's cap is
    1.31x Heart of the Land's at the same em, and its lowercase x-height is
    0.469em against HotL's 0.700em cap. One em value cannot serve both.
    `gap` is the space between runs, in ems of the unscaled size.
    """
    paths, pen_x = [], 0.0
    bounds = None
    upm_ref = None

    for i, run in enumerate(runs):
        text, font_path, tracking, scale = run[:4]
        shift = run[4] if len(run) > 4 else 0.0
        tt, glyphs, upm, hbfont = _load(str(font_path))
        if upm_ref is None:
            upm_ref = upm
        order = tt.getGlyphOrder()
        if i:
            pen_x += gap * upm_ref

        if bounds is None:
            bounds = BoundsPen(glyphs)
        for info, pos in _shape(hbfont, text):
            name = order[info.codepoint]
            # scale about the baseline origin, so baselines stay aligned
            k = scale * upm_ref / upm
            tf = Transform(k, 0, 0, -k,
                           pen_x + pos.x_offset * k,
                           -pos.y_offset * k + shift * upm_ref)
            spen = SVGPathPen(glyphs)
            glyphs[name].draw(TransformPen(spen, tf))
            d = spen.getCommands()
            if d:
                paths.append(d)
            bp = BoundsPen(glyphs)
            glyphs[name].draw(TransformPen(bp, tf))
            if bp.bounds:
                bounds = bp.bounds if not isinstance(bounds, tuple) else (
                    min(bounds[0], bp.bounds[0]), min(bounds[1], bp.bounds[1]),
                    max(bounds[2], bp.bounds[2]), max(bounds[3], bp.bounds[3]))
            pen_x += (pos.x_advance + tracking * upm) * k

    if not isinstance(bounds, tuple):
        raise ValueError("runs produced no outlines")
    x0, y0, x1, y1 = bounds
    w, h = x1 - x0, y1 - y0
    a11y = ('aria-hidden="true"' if aria_hidden
            else f'role="img" aria-label="{html.escape(label or "", quote=True)}"')
    return (
        f'<svg class="{css_class}" {a11y} '
        f'viewBox="{x0:.0f} {y0:.0f} {w:.0f} {h:.0f}" '
        f'style="--sw:{w / upm_ref:.4f};--sh:{h / upm_ref:.4f}" '
        f'preserveAspectRatio="xMinYMid meet" fill="currentColor">'
        f'<path d="{"".join(paths)}"/></svg>'
    )


def centre_shift(text, font_path, from_scale, to_scale, tracking=0.0):
    """Ems to shift a run so its optical centre does not move when its scale
    changes. Scaling happens about the baseline, not about the run's middle."""
    tt, glyphs, upm, hbfont = _load(str(font_path))
    order = tt.getGlyphOrder()
    bounds = BoundsPen(glyphs)
    pen_x = 0.0
    for info, pos in _shape(hbfont, text):
        name = order[info.codepoint]
        tf = Transform(1, 0, 0, -1, pen_x + pos.x_offset, -pos.y_offset)
        glyphs[name].draw(TransformPen(bounds, tf))
        pen_x += pos.x_advance + tracking * upm
    if not bounds.bounds:
        return 0.0
    _, y0, _, y1 = bounds.bounds
    centre = (y0 + y1) / 2 / upm          # ems from the baseline, +ve downward
    return centre * (from_scale - to_scale)


def replace(text, font_path=FONT, css_class="scripttype", tracking=0.0):
    """Outlines, with the real text kept in the markup behind them.

    `render` alone puts the words in an aria-label, which screen readers
    announce but crawlers do not index. For section titles that is a nuisance;
    for the bowl names it would be a mistake -- "Strawberry Fields" is exactly
    the phrase someone searches. So the text ships as a visually-hidden span
    and the drawing is marked decorative. Standard image replacement: what is
    hidden and what is shown are the same words.
    """
    svg = render(text, font_path=font_path, css_class=css_class,
                 tracking=tracking, aria_hidden=True)
    return f'<span class="vh">{html.escape(text, quote=False)}</span>{svg}'


import html  # noqa: E402  (kept beside the only function that needs it)


if __name__ == "__main__":
    import sys
    for t in sys.argv[1:] or ["House Bowls", "Build Your Own"]:
        s = render(t)
        print(f"{t!r}: {len(s)} chars, {s[s.index('style=')+7:s.index('em;')+2]}")
