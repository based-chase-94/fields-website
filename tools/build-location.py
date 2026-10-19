#!/usr/bin/env python3
"""
Fields — the location section.

    python3 tools/build-location.py

Writes two things into site/index.html: the "See you in the fields." heading,
set in Heart of the Land outlines, and the campus map drawn from cached
OpenStreetMap data in source/map/.

Heart of the Land is unicase -- all 26 lowercase glyphs are byte-identical to
their capitals -- so the source text's casing is immaterial; it sets as caps
either way. It is rendered to outlines, not served: nobody has the purchase
record, and absence of an embedded prohibition is not a licence grant. See
tools/scripttype.py.

Why draw it rather than screenshot a tile service:

  * Raster tiles bake every building name, bus stop and parking icon into the
    image. There is no way to take those out afterwards.
  * CARTO's light basemap now needs an API key; its tiles still return 200,
    carrying "API KEY REQUIRED" as artwork. A screenshot would have shipped
    that.
  * Drawing it means the map is in the brand palette by construction, not by
    filtering something else toward it.

The result is ~15 KB gzipped and sharp at any size, which no screenshot is.

Data is cached in source/map/ so a build needs no network. To refresh it, see
docs/map.md for the Overpass queries.

OpenStreetMap data is ODbL: the attribution rendered beside the map is a
licence condition, not decoration. Leave it in.
"""

import json
import math
import pathlib
import re
import sys

try:
    import scripttype
except ImportError:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import scripttype

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "source/map"
INDEX = ROOT / "site/index.html"

MAP_START, MAP_END = "<!-- map:start -->", "<!-- map:end -->"
TITLE_START, TITLE_END = "<!-- loctitle:start -->", "<!-- loctitle:end -->"

# Two lines, each its own svg, so they stack and scale as a block.
TITLE_LINES = ["See you in", "the fields."]

LAT, LON = 39.7451140, -104.8406552   # 12700 E 19th Ave — geocoded, inside "Research 2"
HOME_ID = 133073725                   # OSM way id of that building
# The figure is landscape on desktop and near-square stacked on a phone.
# 1200x1000 sits between the two, so `slice` crops a little either way
# rather than a lot in one.
W, H = 1200, 1000
SPAN_M = 420.0
# `slice` crops the edges, and a half-cut street name is worse than none. The
# anchor alone is not enough to test: the label is centred, so a long name
# overruns a point that is itself comfortably inside. Reserve half the text's
# length on every side instead.
LABEL_SIZE = 30
# Fredoka at 500 measures ~0.56em average advance; plus the 0.05em tracking.
LABEL_EM = 0.61
# A street needs this much straight, on-canvas run to carry its name.
MIN_LABEL_RUN = 90

BG, ROAD, CASING = "#E6D8C9", "#FCF8F3", "#C9B6A3"
FOOT, GREEN = "#D3C2B0", "#BDC8A8"
BLDG, BLDG_LN = "#D9C9B7", "#C2AE99"
INK, FOREST, SUN = "#43503F", "#283628", "#F9E14D"

WIDTH = {"motorway": 26, "trunk": 24, "primary": 22, "secondary": 19,
         "tertiary": 16, "residential": 14, "unclassified": 14,
         "pedestrian": 11, "service": 8}
FOOTCLASS = {"footway", "path", "cycleway", "steps"}

M_PER_UNIT = 6378137.0


def merc(lat, lon):
    return math.radians(lon), math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


CX, CY = merc(LAT, LON)
SCALE = W / (SPAN_M / M_PER_UNIT)


def project(lat, lon):
    x, y = merc(lat, lon)
    return (x - CX) * SCALE + W / 2, (CY - y) * SCALE + H / 2


def d_of(p):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in p)


def load(name):
    p = DATA / name
    return json.loads(p.read_text()).get("elements", []) if p.exists() else []


def build():
    out = [f'<svg class="loc__map" viewBox="0 0 {W} {H}" '
           f'preserveAspectRatio="xMidYMid slice" role="img" '
           f'aria-label="Map of the CU Anschutz campus. Fields is in Research '
           f'Complex 2, on East 19th Avenue.">',
           f'<rect width="{W}" height="{H}" fill="{BG}"/>']

    # parks and lawns
    out.append(f'<g fill="{GREEN}">')
    for w in load("green.json"):
        q = [project(n["lat"], n["lon"]) for n in w.get("geometry", [])]
        if len(q) >= 3:
            out.append(f'<path d="{d_of(q)} Z"/>')
    out.append('</g>')

    # building footprints — shapes only, never names
    home_d = None
    out.append(f'<g fill="{BLDG}" stroke="{BLDG_LN}" stroke-width="1.5" stroke-linejoin="round">')
    for w in load("bldg.json"):
        q = [project(n["lat"], n["lon"]) for n in w.get("geometry", [])]
        if len(q) < 3:
            continue
        if w.get("id") == HOME_ID:
            home_d = d_of(q) + " Z"
            continue
        out.append(f'<path d="{d_of(q)} Z"/>')
    out.append('</g>')

    roads = []
    out.append(f'<g stroke="{FOOT}" stroke-width="3" fill="none" stroke-linecap="round">')
    for w in load("roads.json"):
        hw = w["tags"].get("highway")
        q = [project(n["lat"], n["lon"]) for n in w.get("geometry", [])]
        if len(q) < 2:
            continue
        if all(x < -40 or x > W + 40 or y < -40 or y > H + 40 for x, y in q):
            continue
        if hw in FOOTCLASS:
            out.append(f'<path d="{d_of(q)}"/>')
        else:
            roads.append((hw, w["tags"].get("name"), q))
    out.append('</g>')

    # casing then fill, so junctions knit together
    for stroke, bump in ((CASING, 4), (ROAD, 0)):
        out.append('<g fill="none" stroke-linecap="round" stroke-linejoin="round">')
        for hw, _, q in roads:
            out.append(f'<path d="{d_of(q)}" stroke="{stroke}" '
                       f'stroke-width="{WIDTH.get(hw, 8) + bump}"/>')
        out.append('</g>')

    # street names only — the whole point of drawing this by hand
    seen = {}
    out.append('<g>')
    for hw, nm, q in roads:
        if not nm or "Path" in nm:
            continue
        half = len(nm) * LABEL_SIZE * LABEL_EM / 2
        best = None
        for a, b in zip(q, q[1:]):
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 1:
                continue
            # The label lies along the segment, so its extent projects onto each
            # axis by the direction cosine. Reserving `half` on both axes (the
            # naive guard) throws away every long name; this keeps them.
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            dx = half * abs(ux) + LABEL_SIZE * 0.7 * abs(uy)
            dy = half * abs(uy) + LABEL_SIZE * 0.7 * abs(ux)
            if not (dx < mx < W - dx and dy < my < H - dy):
                continue
            if best is None or L > best[0]:
                best = (L, a, b)
        if not best or best[0] < MIN_LABEL_RUN or seen.get(nm, 0) >= best[0]:
            continue
        seen[nm] = best[0]
        _, a, b = best
        ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        ang = ang - 180 if ang > 90 else (ang + 180 if ang < -90 else ang)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        out.append(f'<text x="{mx:.0f}" y="{my:.0f}" '
                   f'transform="rotate({ang:.1f} {mx:.0f} {my:.0f})" '
                   f'text-anchor="middle" dominant-baseline="middle" '
                   f'font-size="{LABEL_SIZE}" font-weight="500" letter-spacing="0.05em" '
                   f'fill="{INK}" stroke="{ROAD}" stroke-width="7" '
                   f'paint-order="stroke">{nm}</text>')
    out.append('</g>')

    # Outline, never filled: a fill swallows the marker sitting inside it.
    # 9px against 1.5px on every other building. Road casings carry larger
    # stroke-widths, but those draw road bodies in near-white — this is the
    # only heavy dark line on the map.
    assert home_d, f"building {HOME_ID} (Research 2) not found in source/map/bldg.json"
    out.append(f'<path d="{home_d}" fill="none" stroke="{FOREST}" '
               f'stroke-width="9" stroke-linejoin="round"/>')

    px, py = W / 2, H / 2
    out += [f'<circle cx="{px}" cy="{py}" r="58" fill="{FOREST}" opacity="0.13"/>',
            f'<circle cx="{px}" cy="{py}" r="36" fill="{FOREST}" opacity="0.26"/>',
            f'<circle cx="{px}" cy="{py}" r="17" fill="{FOREST}"/>',
            f'<circle cx="{px}" cy="{py}" r="7" fill="{BG}"/>',
            '</svg>']

    return "\n".join(out), len(roads), len(seen)


def inject(s, start, end, block, what):
    assert s.count(start) == 1 and s.count(end) == 1, f"{what} markers missing or duplicated"
    out, n = re.subn(re.escape(start) + r".*?" + re.escape(end),
                     lambda _: start + "\n" + block + "\n" + end, s, flags=re.S)
    assert n == 1 and block in out, f"{what} substitution did not apply"
    return out


def title():
    # replace(), not render(): the words ship as hidden text behind the
    # drawing so crawlers and screen readers get them.
    lines = [scripttype.replace(t, font_path=scripttype.HEART,
                                css_class="loc__titleline")
             for t in TITLE_LINES]
    return "\n".join(lines)


def main():
    s = INDEX.read_text(encoding="utf-8")

    t = title()
    s = inject(s, TITLE_START, TITLE_END, t, "location title")

    svg, nroads, nlabels = build()
    s = inject(s, MAP_START, MAP_END, svg, "map")

    INDEX.write_text(s, encoding="utf-8")
    print(f"title: {len(TITLE_LINES)} lines in Heart of the Land outlines "
          f"({len(t)/1024:.1f} KB)")
    print(f"map:   {nroads} roads, {nlabels} street labels ({len(svg)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
