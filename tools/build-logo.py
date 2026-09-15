#!/usr/bin/env python3
"""
Fields — logo build step.

Takes the vector master in source/logo/ and emits the web copies:

  * site/assets/img/fields-primary-white.svg    for dark grounds
  * site/assets/img/fields-primary-forest.svg   for light grounds
  * site/assets/img/favicon.svg                 the F swash on Forest
  * the inline <svg> inside site/index.html, between the logo markers,
    filled with currentColor so CSS drives the colour

    python3 tools/build-logo.py

The master is Inkscape output carrying a lot of editor metadata and a
hard-coded #000000 on every path. None of that should ship, but none of the
geometry is touched — the viewBox stays exactly as drawn, because its padding
is the logo's clearspace.
"""

import pathlib
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
MASTER = ROOT / "source/logo/Fields Primary Logo.svg"
IMG = ROOT / "site/assets/img"
INDEX = ROOT / "site/index.html"

SVG = "http://www.w3.org/2000/svg"
DROP_NS = ("inkscape", "sodipodi")

# The master splits cleanly in two: path15-20 are the "Fields" script itself,
# path2-14 are the GRAINS + GREENS line beneath it. That lets the two be
# coloured independently, which is what the brand lockup wants.
WORDMARK_PATHS = {"path15", "path16", "path17", "path18", "path19", "path20"}

# name -> (wordmark fill, sub-line fill)
VARIANTS = {
    "brand":  ("#F9E14D", "#FFFFFF"),   # Sunshine script, white sub-line
    "white":  ("#FFFFFF", "#FFFFFF"),
    "forest": ("#283628", "#283628"),
}

FOREST = "#283628"

# The lockup is a wordmark with no standalone symbol, so the favicon is the
# "F" and its swash — path15, the only glyph that reads at 32 px. This viewBox
# squares and centres that glyph with ~15% breathing room; the numbers come
# from measuring the rendered path (x 25.9, y 17.1, 135.8 x 127.0) and must be
# re-measured if the master artwork ever changes.
FAVICON_VIEWBOX = "5.55 -7.65 176.5 176.5"
FAVICON_GLYPH = "path15"


def clean(wordmark_fill, sub_fill):
    """Return the master as a minimal <svg> tree, the two groups filled
    independently."""
    ET.register_namespace("", SVG)
    tree = ET.parse(MASTER)
    root = tree.getroot()

    # Editor furniture: namedview, defs, and anything in an editor namespace.
    for parent in root.iter():
        for child in list(parent):
            tag = child.tag
            if tag.startswith("{") and not tag.startswith("{%s}" % SVG):
                parent.remove(child)
            elif tag in ("{%s}defs" % SVG,) and len(child) == 0:
                parent.remove(child)

    for el in root.iter():
        for attr in list(el.attrib):
            if attr.startswith("{") or attr.split(":")[0] in DROP_NS:
                del el.attrib[attr]
        # Every path carries the same hard-coded black style. Drop it and fill
        # by which half of the lockup the path belongs to.
        if el.tag == "{%s}path" % SVG:
            el.attrib.pop("style", None)
            pid = el.get("id", "")
            el.set("fill", wordmark_fill if pid in WORDMARK_PATHS else sub_fill)
        # Layer/group ids are Inkscape's, not ours.
        if el.tag == "{%s}g" % SVG:
            el.attrib.pop("id", None)

    root.attrib.pop("id", None)
    # No explicit xmlns here — register_namespace already emits the default one,
    # and setting it again produces a duplicate attribute that strict XML
    # parsers reject (HTML's lenient parser hides this, .svg files don't).
    # Geometry untouched: viewBox is the clearspace, width/height are hints.
    return root


def serialise(root):
    out = ET.tostring(root, encoding="unicode")
    out = re.sub(r"\s*\n\s*", "", out)          # ET keeps Inkscape's whitespace
    out = out.replace("><", ">\n<")
    return out


def favicon():
    """The F glyph alone, knocked out of a Forest tile."""
    root = clean("#FFFFFF", "#FFFFFF")
    group = root.find(".//{%s}g" % SVG)
    for el in root.iter():
        for child in list(el):
            if child.tag == "{%s}path" % SVG and child.get("id") != FAVICON_GLYPH:
                el.remove(child)
    root.set("viewBox", FAVICON_VIEWBOX)
    root.set("width", "512")
    root.set("height", "512")
    rect = ET.Element("{%s}rect" % SVG)
    rect.set("x", "5.55"); rect.set("y", "-7.65")
    rect.set("width", "176.5"); rect.set("height", "176.5")
    rect.set("fill", FOREST)
    (group if group is not None else root).insert(0, rect)
    dest = IMG / "favicon.svg"
    dest.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + serialise(root) + "\n")
    print(f"  {dest.relative_to(ROOT)}")
    return dest


def rasterise(src):
    """iOS home-screen icons must be PNG; everything else takes the SVG."""
    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        print("  ! rsvg-convert not found — PNG icons not rebuilt.")
        print("    brew install librsvg, then re-run, to regenerate them.")
        return
    for px, name in ((180, "apple-touch-icon.png"),):
        dest = IMG / name
        subprocess.run(
            [rsvg, "-w", str(px), "-h", str(px), "-o", str(dest), str(src)],
            check=True,
        )
        print(f"  {dest.relative_to(ROOT)}")


def main():
    IMG.mkdir(parents=True, exist_ok=True)

    for name, (wm, sub) in VARIANTS.items():
        dest = IMG / f"fields-primary-{name}.svg"
        dest.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n' + serialise(clean(wm, sub)) + "\n"
        )
        print(f"  {dest.relative_to(ROOT)}  ({dest.stat().st_size // 1024} KB)")

    # Inline copy: currentColor means one CSS declaration recolours it, and the
    # logo paints with the document instead of waiting on a second request.
    inline = clean("var(--logo-ink, #F9E14D)", "var(--logo-sub-ink, #FFFFFF)")
    inline.attrib.pop("width", None)
    inline.attrib.pop("height", None)
    inline.set("class", "hero__logo")
    inline.set("role", "img")
    inline.set("aria-label", "Fields — grains + greens")

    html = INDEX.read_text()
    block = serialise(inline)
    new, n = re.subn(
        r"(<!-- logo:start -->).*?(<!-- logo:end -->)",
        lambda m: m.group(1) + "\n" + block + "\n    " + m.group(2),
        html,
        flags=re.S,
    )
    if not n:
        raise SystemExit("index.html is missing the <!-- logo:start/end --> markers")
    INDEX.write_text(new)
    print(f"  {INDEX.relative_to(ROOT)}  (inline logo, {len(block) // 1024} KB)")

    rasterise(favicon())


if __name__ == "__main__":
    main()
