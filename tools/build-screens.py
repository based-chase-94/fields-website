#!/usr/bin/env python3
"""
Fields — the in-store menu board pages.

    python3 tools/build-screens.py

Writes site/screens/<CODE>/<board>/index.html: one page per TV, played by the
XOGO Mini behind each TV as a URL asset. They replace the baked 4K videos: the
grass loop plays as the page background and the browser draws the board on top,
so a menu change is an edit to source/menu/menu.json and a push, not a re-bake.

The layout is fields-digital-menu's tools/build-grass-latest.py, unchanged:
a fixed 3840x2160 stage using Figma's numbers (frame "FINAL - 1" for House
Bowls), scaled to the screen in the page. Only the words now come from
menu.json, the same file the website menu is built from.

Lettering. Midstar and Heart of the Land are licensed, and this repo is public,
so neither font file can ship (see tools/scripttype.py). They are drawn as SVG
outlines instead. To put each outline exactly where the browser would set the
text, the build first lays the board out with the real fonts in headless
Chromium (tools/screens-measure.mjs), reads each line's baseline and start,
then places the outline there. Fredoka is open-licensed (OFL) and is served as
a webfont, so descriptions and prices stay live text.

Needs: source/fonts/{Midstar.otf, Heart-of-the-Land-Regular.otf,
Fredoka-VariableFont_wdth,wght.ttf} (gitignored), the loops from
tools/encode-screen-loops.sh, fonttools + uharfbuzz + brotli (pip), and Node
with Playwright.
"""

import hashlib
import html
import json
import re
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import scripttype  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "source/menu/menu.json"
SRC = ROOT / "source/screens"
FONTS = ROOT / "source/fonts"
LOOPS = ROOT / "source/video/screens"
SITE = ROOT / "site/screens"
ASSETS = SITE / "assets"       # content-hashed names, cached for a year
CODE = "7upeczte"              # unlisted path segment; change it (and XOGO's URLs) if it ever leaks
PAGES = SITE / CODE            # no-cache HTML, version.json, sw.js

W, H = 3840, 2160
WHITE, SUN = "#ffffff", "#f9e14d"
FREDOKA = FONTS / "Fredoka-VariableFont_wdth,wght.ttf"
MID = "font-family: 'Midstar'; font-weight: 400"
HOTL = "font-family: 'Heart of the Land'; font-weight: 400"
FONTFILES = {"Midstar": scripttype.FONT, "Heart of the Land": scripttype.HEART}

esc = lambda s: html.escape(s, quote=False)
money = lambda p: f"${p:.2f}"


# ------------------------------------------------------------------ boards
# Each board returns its stage HTML. An element with data-outline="<font>" has
# its text drawn as outlines; one text node per line (lines split with <br>).

def house_bowls(m, img):
    """Board 1, left TV. fields-digital-menu build-grass-latest.py signature()."""
    hb = m["houseBowls"]

    def item(it):
        lines = it["boardLines"]
        if " ".join(lines) != it["ingredients"]:
            raise SystemExit(
                f"{it['name']}: boardLines don't spell out ingredients.\n"
                f"  ingredients: {it['ingredients']}\n  boardLines:  {' '.join(lines)}")
        return (
            '<div style="display: flex; flex-direction: column; gap: 36px">'
            '<div style="display: flex; align-items: flex-start; gap: 36px">'
            f'<span data-outline="Heart of the Land" style="{HOTL}; font-size: 106px; line-height: 73.6px; white-space: nowrap">{esc(it["name"])}</span>'
            '<span style="flex: 1 0 0; min-width: 1px; height: 76px"></span>'
            f'<span style="position: relative; top: 1px; font-size: 106px; font-weight: 600; line-height: 73.6px; color: {SUN}; white-space: nowrap">{money(it["price"])}</span></div>'
            '<p data-fit style="margin: 0; font-size: 68px; font-weight: 400; line-height: normal; letter-spacing: -1px; white-space: nowrap; font-feature-settings: \'dlig\' 1">'
            + "<br>".join(esc(l) for l in lines) + "</p></div>")

    b = (f'<h2 data-outline="Midstar" style="position: absolute; left: 137px; top: 231.1px; margin: 0; {MID}; font-size: 273px; '
         f'line-height: 121.8px; color: {SUN}; white-space: nowrap">{esc(hb["title"])}</h2>\n')
    b += (f'<p data-outline="Heart of the Land" style="position: absolute; right: 131px; top: 185px; margin: 0; {HOTL}; font-size: 106px; '
          f'line-height: 120px; text-align: right; white-space: nowrap">'
          + "<br>".join(esc(l.upper()) for l in hb["boardKicker"]) + "</p>\n")
    b += ('<div data-column style="position: absolute; left: 130px; top: 589px; width: 3579px; display: grid; '
          'grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 130px; row-gap: 107px">')
    b += "".join(item(it) for it in hb["items"])
    b += "</div>\n"
    # The vegetarian mark follows the name of each vegetarian bowl: Figma puts it 31 px after
    # FIELDS NOTES and 7 px above the name's box (2764, 1512). place_marks() sets left/top.
    for i, it in enumerate(hb["items"]):
        if it.get("vegetarian"):
            b += f'<img data-mark="{esc(it["name"])}" data-dx="31.1" data-dy="-7" src="{img["vegetarian"]}" alt="Vegetarian" style="position: absolute; left: 0px; top: 0px; width: 95px; height: 95px; display: block">\n'
    b += (f'<p style="position: absolute; left: 62px; top: {H - 122}px; margin: 0; font-size: 58px; font-weight: 500; line-height: normal; '
          f'letter-spacing: -1px; color: {SUN}; white-space: nowrap; font-feature-settings: \'dlig\' 1">{esc(hb["note"])}</p>\n')
    return b


# ------------------------------------------------------------------ boards 2 and 3: the steps
# fields-digital-menu build-grass-latest.py build() and beverages(), frames "FINAL - 2" and "FINAL - 3".

def emph(t):
    """'Pick a *field base*' -> the starred words in medium-weight Sunshine."""
    parts = t.split("*")
    if len(parts) % 2 == 0:
        raise SystemExit(f"unbalanced * in {t!r}")
    return "".join(esc(x) if i % 2 == 0 else f'<span style="font-weight: 500; color: {SUN}">{esc(x)}</span>'
                   for i, x in enumerate(parts))


def emph_heading(t):
    """Same, for a Heart of the Land heading: the starred words in Sunshine (the face has one weight)."""
    parts = t.upper().split("*")
    return "".join(esc(x) if i % 2 == 0 else f'<span style="color: {SUN}">{esc(x)}</span>' for i, x in enumerate(parts))


def plain(t):
    return t.replace("*", "")


def vec(img, key, x, y, w, h, alt=""):
    return (f'<img src="{img[key]}" alt="{esc(alt)}" style="position: absolute; left: {x:g}px; top: {y:g}px; '
            f'width: {w:g}px; height: {h:g}px; display: block">\n')


def hotl(x, y, size, inner, extra=""):
    return (f'<p data-outline="Heart of the Land" style="position: absolute; left: {x}px; top: {y}px; margin: 0; {HOTL}; '
            f'font-size: {size}px; line-height: 123.6px;{extra} white-space: nowrap">{inner}</p>\n')


def step(img, n, st, px, py, ph, x, hy, ty=None):
    """A number pill, a 130px Heart of the Land heading and (optionally) an 80px Fredoka line."""
    if plain(st["boardTitle"]).lower() != st["title"].lower():
        raise SystemExit(f"step {n}: boardTitle {st['boardTitle']!r} doesn't match title {st['title']!r}")
    b = vec(img, f"step{n}", px, py, 231, ph, alt=str(n)) + hotl(x, hy + 1, 130, emph_heading(st["boardTitle"]))  # Figma's glyphs sit 1px lower
    if ty is not None:
        if "boardDetail" not in st:
            raise SystemExit(f"step {n} needs a boardDetail")
        b += (f'<p data-fit style="position: absolute; left: {x}px; top: {ty}px; margin: 0; font-size: 80px; font-weight: 400; line-height: normal; '
              f'letter-spacing: -1px; white-space: nowrap; font-feature-settings: \'dlig\' 1">{emph(st["boardDetail"])}</p>\n')
    return b


def column_grid(x, y, width, cols, row_gap, cells):
    """Figma's 74px ingredient grids, filled column by column."""
    rows = -(-len(cells) // cols)
    cells_html = "".join(f'<div style="grid-column: {i // rows + 1}; grid-row: {i % rows + 1}">{esc(c)}</div>' for i, c in enumerate(cells))
    return (f'<div style="position: absolute; left: {x}px; top: {y}px; width: {width}px; display: grid; '
            f'grid-template-columns: repeat({cols}, minmax(0, 1fr)); column-gap: 76px; row-gap: {row_gap}px; align-items: start; '
            f'font-size: 74px; font-weight: 400; line-height: 90px; white-space: nowrap">{cells_html}</div>\n')


def lst(m, title):
    for l in m["lists"]:
        if l["title"] == title:
            return l
    raise SystemExit(f"menu.json has no list titled {title!r}")


def grow_your_own(m, img):
    """Board 2, centre TV: steps 1 and 2."""
    byo = m["buildYourOwn"]
    s1, s2 = byo["steps"][0], byo["steps"][1]
    # "Grow your Own", "Starts at" and the price are Figma's lettering, exported as vectors.
    if byo["startsAt"] != 9.95:
        raise SystemExit("buildYourOwn.startsAt changed: the board's price is Figma lettering "
                         "(source/screens/vectors/price-6.svg). Export the new price from Figma first.")
    b = vec(img, "grow-2", 147, 167.05, 615.076, 249.191, alt="Grow")
    b += vec(img, "your", 801.47, 298, 281.533, 74.069, alt="your")
    b += vec(img, "own", 1129, 159.43, 489.883, 248.033, alt="Own")
    b += vec(img, "starts-at-6", 2969, 244.55, 258.121, 92.342, alt="Starts at")
    b += vec(img, "price-6", 3270.76, 219.61, 359.237, 136.31, alt=money(byo["startsAt"]))
    b += step(img, 1, s1, 180, 593, 128.452, 464, 591, 778)
    greens = lst(m, "Greens + Grains")["items"]
    if len(greens) > 6:
        raise SystemExit("Greens + Grains: the board has room for 6")
    b += column_grid(464, 974, 565, 1, 53, greens)
    b += step(img, 2, s2, 1920, 592, 129.712, 2203, 591, 782)
    b += ('<p style="position: absolute; right: 210px; top: 805px; margin: 0; font-size: 55px; font-weight: 400; line-height: normal; '
          'letter-spacing: -1px; text-align: right; white-space: nowrap">' + "<br>".join(esc(l) for l in s2["boardAside"]) + "</p>\n")
    toppings = lst(m, "Field Ingredients")["items"]
    if len(toppings) > 18:
        raise SystemExit("Field Ingredients: the board has room for 18")
    b += column_grid(2203, 974, 1571, 2, 32, toppings)
    b += hotl(180, 1928 + 1, 75, f'<span style="color: {SUN}; white-space: pre">{esc(byo["boardHours"].upper())}</span>')
    return b


STEP4_TOP, TITLE_TOP, DRESS_ROW = 1486, 358, 75


def proteins_upgrades(m, img):
    """Board 3, right TV: steps 3 and 4."""
    s3, s4 = m["buildYourOwn"]["steps"][2], m["buildYourOwn"]["steps"][3]
    curly = lambda t: t.replace("'", "’")

    def title(x, t):
        return (f'<h2 data-outline="Midstar" style="position: absolute; left: {x}px; top: {TITLE_TOP}px; margin: 0; {MID}; font-size: 110px; '
                f'line-height: normal; letter-spacing: -1px; color: {SUN}; white-space: nowrap">{esc(t)}</h2>\n')

    def prices(x, items):
        if len(items) > 7:
            raise SystemExit("Proteins and Upgrades: the board has room for 7 rows each")
        return (f'<div style="position: absolute; left: {x}px; top: 544px; width: 1483px; display: flex; flex-direction: column; gap: 28px">'
                + "".join(f'<div data-row style="display: flex; align-items: center; justify-content: space-between; white-space: nowrap">'
                          f'<span style="font-size: 74px; font-weight: 400; line-height: 90px">{esc(curly(it["name"]))}</span>'
                          f'<span style="font-size: 68px; font-weight: 600; line-height: 73.6px; color: {SUN}">+{money(it["price"])}</span></div>'
                          for it in items) + "</div>\n")

    b = step(img, 3, s3, 193, 192, 130.972, 476, 192)
    b += vec(img, "order-online", 3102.49, 179, 537.43, 49.926, alt="Order online @")
    b += vec(img, "fieldsbowls", 2904, 249.66, 734.183, 56.345, alt="fieldsbowls.com")
    for x, t in ((458, "Proteins"), (2140, "Upgrades")):
        b += title(x, t)
        b += prices(x + 18, lst(m, t)["items"])
    # Step 4 is centred on y 1608 in Figma: its heading's top is 1608 minus half the block (147 + one 80px line).
    b += step(img, 4, s4, 193, STEP4_TOP + 6, 128.485, 476, STEP4_TOP, STEP4_TOP + 147)
    # Dressings: Figma's 2-column grid, 62px. "|" breaks a name over two lines. The last two of the
    # second column are one 93px-leading block that Figma places 9px above its row, so its first
    # line lines up with the two-line name beside it.
    dress = lst(m, "Dressings")
    c1, c2 = dress["boardColumns"]
    if len(c1) + len(c2) != len(dress["items"]):
        raise SystemExit(f"Dressings: boardColumns has {len(c1) + len(c2)} names, items has {len(dress['items'])}")
    if len(c1) != 5 or len(c2) != 6:
        raise SystemExit("Dressings: the board layout is 5 names on the left, 6 on the right")
    cell = lambda t: (lambda n: f'<div style="height: {DRESS_ROW * n + 32 * (n - 1)}px">{"<br>".join(esc(x) for x in t.split("|"))}</div>')(t.count("|") + 1)
    b += ('<div style="position: absolute; left: 2157px; top: 1481px; width: 1683px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); '
          f'column-gap: 76px; align-items: start; font-size: 62px; font-weight: 400; line-height: {DRESS_ROW}px; white-space: nowrap">'
          '<div data-col style="display: flex; flex-direction: column; gap: 32px">' + "".join(cell(t) for t in c1)
          + '</div><div data-col style="display: flex; flex-direction: column; gap: 32px">' + "".join(cell(t) for t in c2[:4])
          + f'<div style="margin-top: -9px; line-height: 93px">{esc(c2[4])}<br>{esc(c2[5])}</div></div></div>\n')
    notes = list(m["footnotes"])
    notes[-1] = notes[-1].rstrip(".")  # as on the board
    b += ('<p style="position: absolute; left: 193px; top: 1997px; transform: translateY(-50%); margin: 0; font-size: 38px; font-weight: 400; '
          'line-height: normal; white-space: nowrap">' + "<br>".join(esc(n) for n in notes) + "</p>\n")
    return b


BOARDS = [
    # slug, title, builder, poster
    ("house-bowls", "House Bowls", house_bowls, "grass-house-bowls.jpg"),
    ("grow-your-own", "Grow Your Own", grow_your_own, "grass-grow-your-own.jpg"),
    ("proteins-upgrades", "Proteins + Upgrades", proteins_upgrades, "grass-proteins-upgrades.jpg"),
]


# ------------------------------------------------------------------ assets

def hashed(src: pathlib.Path, name: str, data: bytes | None = None) -> str:
    """Copy into site/screens/assets/ as <stem>.<hash><ext>; return its URL."""
    data = src.read_bytes() if data is None else data
    h = hashlib.sha256(data).hexdigest()[:10]
    p = pathlib.Path(name)
    out = ASSETS / f"{p.stem}.{h}{p.suffix}"
    if not out.exists():
        out.write_bytes(data)
    return f"/screens/assets/{out.name}"


def fredoka_woff2() -> bytes:
    f = TTFont(FREDOKA, recalcTimestamp=False)  # same bytes every build, so the same URL
    f.flavor = "woff2"
    with tempfile.NamedTemporaryFile(suffix=".woff2") as t:
        f.save(t.name)
        return pathlib.Path(t.name).read_bytes()


def outline_svg(text, family, size, tracking=0.0):
    """The words as one <svg> of paths, positioned from its baseline origin.
    `tracking` is CSS letter-spacing in em, which outlines have to bake in."""
    font = FONTFILES[family]
    s = scripttype.render(text, font_path=font, css_class="ol", aria_hidden=True, tracking=tracking)
    upm = scripttype._load(str(font))[2]
    vb = s.split('viewBox="')[1].split('"')[0]
    x0, y0, w, h = map(float, vb.split())
    k = size / upm
    return s, x0 * k, y0 * k, w * k, h * k


# ------------------------------------------------------------------ page

def metrics(path):
    """CSS overrides that pin a face to its hhea ascent/descent/line gap.

    Browsers disagree on which of a font's three sets of vertical metrics to
    use: macOS reads hhea, while Chromium on Linux and Android follows the
    USE_TYPO_METRICS flag to the OS/2 typo values. Midstar's typo descender is
    3.5x its hhea one, which moves its baseline by about 100 px at 273 px in a
    fixed line-height. The board positions were matched to Figma on a Mac, so
    hhea is the reference, and pinning it makes every player lay out alike.
    """
    t = TTFont(path)
    upm, h = t["head"].unitsPerEm, t["hhea"]
    pc = lambda v: f"{abs(v) * 100 / upm:.4f}%"
    return f"ascent-override:{pc(h.ascent)};descent-override:{pc(h.descent)};line-gap-override:{pc(h.lineGap)}"


def draft(body, fredoka_url):
    """The board with the real fonts, for measuring (never deployed)."""
    faces = "".join(
        f"@font-face{{font-family:'{fam}';src:url({path.as_uri()});font-display:block;{metrics(path)}}}"
        for fam, path in FONTFILES.items())
    return (f"<!doctype html><meta charset=utf-8><style>{faces}"
            f"@font-face{{font-family:'Fredoka';src:url({FREDOKA.as_uri()});font-weight:300 700;font-display:block;{metrics(FREDOKA)}}}"
            f"body{{margin:0}}#stage{{width:{W}px;height:{H}px;position:relative;overflow:hidden;color:{WHITE};font-family:'Fredoka'}}</style>"
            f"<div id=stage>{body}</div>")


def measure(draft_html):
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "draft.html"
        p.write_text(draft_html)
        r = subprocess.run(["node", str(ROOT / "tools/screens-measure.mjs"), str(p)],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"measuring failed:\n{r.stderr}")
        out = r.stdout
    return json.loads(out)


def final_body(body, m):
    """Hide each outlined element's live text and draw its runs as outlines on top.

    The element stays in place (hidden, but sized to what it measured with the real
    font) so the rows around it lay out exactly as they did when measured.
    """
    parts = body.split('data-outline="')
    out, svgs = parts[0], []
    assert len(parts) - 1 == len(m["outlines"])
    for part, el in zip(parts[1:], m["outlines"]):
        fam, rest = part.split('"', 1)
        assert el["font"] == fam, (el["font"], fam)
        assert rest.startswith(' style="'), rest[:40]
        rest = rest.replace(' style="', f' style="visibility: hidden; width: {el["w"]:.2f}px; height: {el["h"]:.2f}px; ', 1)
        out += f'data-o="{fam}"' + rest
        for run in el["lines"]:
            text = html.unescape(run["text"])
            if not run["pre"]:
                text = re.sub(r"\s+", " ", text)
            s, x0, y0, w, h = outline_svg(text, fam, run["size"], run["tracking"])
            left, top = run["x"] + x0, run["baseline"] + y0
            s = s.replace('<svg class="ol"', f'<svg class="ol" style="left:{left:.2f}px;top:{top:.2f}px;width:{w:.2f}px;height:{h:.2f}px;color:{run["color"]}"', 1)
            # scripttype sizes in em via --sw/--sh; drop that, the overlay is absolutely placed.
            s = s.replace(s[s.index(' style="--sw'):s.index('" preserveAspectRatio') + 1], "", 1)
            svgs.append(s)
    return out + '<div class="outlines" aria-hidden="true">' + "".join(svgs) + "</div>\n"


def place_marks(body, m):
    """Put each data-mark image beside the outlined name it belongs to."""
    names = {html.unescape("".join(l["text"] for l in o["lines"])): o for o in m["outlines"]}

    def put(mt):
        o = names[html.unescape(mt.group(1))]
        dx, dy = float(mt.group(2)), float(mt.group(3))
        return mt.group(0).replace("left: 0px; top: 0px", f"left: {o['x'] + o['w'] + dx:.1f}px; top: {o['y'] + dy:.1f}px")
    return re.sub(r'data-mark="([^"]+)" data-dx="([-\d.]+)" data-dy="([-\d.]+)"[^>]*>', put, body)


def check_fit(m):
    """Fail the build rather than ship a line that runs into its neighbour."""
    errors = [f"  {o['what']}: {o['over']:.0f}px too wide" for o in m["overflow"]]
    if errors:
        raise SystemExit("Lines overflow their column:\n" + "\n".join(errors))


def page(title, body, board, poster, loops, fredoka_url, runtime, build):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · Fields menu board</title>
<link rel="preload" href="{fredoka_url}" as="font" type="font/woff2" crossorigin>
<style>
@font-face{{font-family:'Fredoka';src:url({fredoka_url}) format('woff2');font-weight:300 700;font-display:block;{metrics(FREDOKA)}}}
html,body{{margin:0;height:100%;background:#1d2716;overflow:hidden;cursor:none}}
#stage{{position:absolute;left:50%;top:50%;width:{W}px;height:{H}px;margin:-{H // 2}px 0 0 -{W // 2}px;overflow:hidden;
  background:#1d2716 url({poster}) center/cover no-repeat;color:{WHITE};font-family:'Fredoka',sans-serif;
  transform-origin:50% 50%;opacity:0;transition:opacity .4s}}
#stage.ready{{opacity:1}}
#bg{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
#board{{position:absolute;inset:0}}
.outlines{{position:absolute;inset:0;pointer-events:none}}
.ol{{position:absolute;display:block;overflow:visible}}
.vh{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}}
#dot{{position:absolute;right:40px;bottom:40px;width:14px;height:14px;border-radius:50%;background:#7bc96f;opacity:.35}}
#dot.offline{{background:#f0a43a;opacity:.7}}
.check #safe{{position:absolute;inset:{H * 0.05:.0f}px {W * 0.05:.0f}px;outline:4px dashed #f0f;pointer-events:none}}
.check #info{{position:absolute;left:{W * 0.05 + 20:.0f}px;top:{H * 0.05 + 20:.0f}px;font:500 48px/1.3 Fredoka,sans-serif;color:#f0f;background:#000a;padding:12px 20px}}
</style>
</head>
<body>
<div id="stage" data-board="{board}" data-build="{build}" data-loop-hd="{loops.get(1080, '')}" data-loop-uhd="{loops.get(2160, '')}">
<video id="bg" muted loop playsinline autoplay preload="auto" disablepictureinpicture aria-hidden="true"></video>
<div id="board">
{body}</div>
<div id="dot" aria-hidden="true"></div>
</div>
<script>
{runtime}
</script>
</body>
</html>
"""


def main():
    menu = json.loads(DATA.read_text())
    for f in [*FONTFILES.values(), FREDOKA]:
        if not f.exists():
            raise SystemExit(f"{f.relative_to(ROOT)} missing: copy it from the style guide (it stays gitignored).")

    if f"/screens/{CODE}/*" not in (ROOT / "site/_headers").read_text():
        raise SystemExit(f"site/_headers has no /screens/{CODE}/* block: the pages would be indexable")

    if ASSETS.exists():
        shutil.rmtree(ASSETS)
    if PAGES.exists():
        shutil.rmtree(PAGES)
    ASSETS.mkdir(parents=True)
    PAGES.mkdir(parents=True)

    fredoka_url = hashed(FREDOKA, "fredoka.woff2", fredoka_woff2())
    img = {f.stem: hashed(f, f.name) for f in sorted((SRC / "vectors").glob("*.svg"))}
    runtime = (SRC / "screen.js").read_text()
    precache, built = [fredoka_url, *img.values()], []

    for slug, title, builder, poster_name in BOARDS:
        body = builder(menu, img)
        m = measure(draft(body, fredoka_url))
        check_fit(m)
        poster = hashed(SRC / poster_name, poster_name)
        loops = {}
        for hgt in (1080, 2160):
            f = LOOPS / f"{slug}-{hgt}.mp4"
            if f.exists():
                if f.stat().st_size > 25 * 1024 * 1024:
                    raise SystemExit(f"{f.name} is over Cloudflare's 25 MiB per-file limit")
                loops[hgt] = hashed(f, f"grass-{slug}-{hgt}.mp4")
            else:
                print(f"  ! {f.relative_to(ROOT)} missing: the page shows the still. Run tools/encode-screen-loops.sh")
        html_body = final_body(place_marks(body, m), m)
        precache += [poster, *loops.values(), f"/screens/{CODE}/{slug}/"]
        built.append((slug, title, html_body, poster, loops))

    # One build id for everything: when it changes, every TV reloads.
    h = hashlib.sha256(json.dumps([b[2] for b in built]).encode() + runtime.encode()
                       + "".join(sorted(precache)).encode() + (SRC / "sw.js").read_bytes())
    build = h.hexdigest()[:12]

    for slug, title, html_body, poster, loops in built:
        d = PAGES / slug
        d.mkdir()
        (d / "index.html").write_text(page(title, html_body, slug, poster, loops, fredoka_url, runtime, build))
        print(f"  site/screens/{CODE}/{slug}/  ({', '.join(f'{k}p' for k in loops) or 'still only'})")

    (PAGES / "version.json").write_text(json.dumps({"build": build}) + "\n")
    sw = (SRC / "sw.js").read_text().replace("__BUILD__", build).replace(
        "__PRECACHE__", json.dumps(sorted(set(precache))))
    (PAGES / "sw.js").write_text(sw)
    print(f"  build {build}")


if __name__ == "__main__":
    main()
