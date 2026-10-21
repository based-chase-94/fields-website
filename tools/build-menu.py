#!/usr/bin/env python3
"""
Fields — menu section.

    python3 tools/build-menu.py

Renders source/menu/menu.json into site/index.html between the menu markers.

Plain semantic HTML, written at build time rather than assembled by JavaScript
in the browser. A menu is the page's actual content: it has to be in the markup
for search engines, for screen readers, and for anyone whose JS fails. There is
nothing a client-side render would buy here.
"""

import html
import json
import pathlib
import re
import sys

try:
    import scripttype
except ImportError:                      # running from outside tools/
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import scripttype

WARNINGS = []


def outline(text, font, cls, tracking=0.0):
    """Text as outlines with the words kept behind them, or plain escaped text
    if the font is missing. source/fonts/ is gitignored, so a fresh clone has
    neither face and must still build rather than failing."""
    try:
        return scripttype.replace(text, font_path=font, css_class=cls,
                                  tracking=tracking)
    except Exception as e:
        WARNINGS.append(f"{text!r} set as plain text — {type(e).__name__}: {e}")
        return esc(text)


def script_title(text, cls, hid):
    """Section title in Midstar — the script is the point here, so this one
    face stays."""
    body = outline(text, scripttype.FONT, "scripttype")
    mod = f" {cls}--script" if "<svg" in body else ""
    return f'<h2 class="{cls}{mod}" id="{hid}">{body}</h2>'


def caps(text, tracking=0.03):
    """An all-caps line in Heart of the Land. The face is unicase, so the
    source casing is immaterial -- it sets as capitals either way."""
    return outline(text, scripttype.HEART, "capsline", tracking)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "source/menu/menu.json"
INDEX = ROOT / "site/index.html"

START = "<!-- menu:start -->"
END = "<!-- menu:end -->"

ORDER_START, ORDER_END = "<!-- order:start -->", "<!-- order:end -->"
CTA_START, CTA_END = "<!-- ordercta:start -->", "<!-- ordercta:end -->"

# ChowNow is still being built. Until there is a real destination this stays
# None and the call to action renders as a disabled control, never a link --
# a button that 404s or goes nowhere is worse than one that says "not yet".
# Set it to the ordering URL and the same markup becomes a live link.
ORDER_URL = None


def money(v):
    # Always two decimals. "$6" next to "$4.25" in the same column reads as a
    # typo rather than a rounder price.
    return f"${v:,.2f}"


def esc(s):
    return html.escape(str(s), quote=False)


def bowls(d):
    o = [script_title(d["title"], "menu__title", "menu-bowls"),
         f'<p class="menu__kicker">{esc(d["kicker"])}</p>',
         '<ul class="bowls">']
    for b in d["items"]:
        veg = ' <abbr class="bowls__veg" title="Vegetarian">V</abbr>' if b.get("vegetarian") else ""
        o += ['  <li class="bowls__item">',
              '    <div class="bowls__head">',
              f'      <h3 class="bowls__name">{caps(b["name"])}{veg}</h3>',
              '      <span class="bowls__rule" aria-hidden="true"></span>',
              f'      <p class="bowls__price">{money(b["price"])}</p>',
              '    </div>',
              f'    <p class="bowls__ingredients">{esc(b["ingredients"])}</p>',
              '  </li>']
    o += ['</ul>', f'<p class="menu__note">{esc(d["note"])}</p>']
    return o


def byo(d):
    o = ['<div class="byo__head">',
         "  " + script_title(d["title"], "menu__title", "menu-byo"),
         f'  <p class="byo__from"><span class="byo__from-label">Starts at</span>'
         f'<span class="price"><span class="price__cur">$</span>'
         f'{d["startsAt"]:,.2f}</span></p>',
         '</div>',
         '<ol class="steps">']
    for s in d["steps"]:
        aside = f'<span class="steps__aside">{esc(s["aside"])}</span>' if s.get("aside") else ""
        o += ['  <li class="steps__item">',
              f'    <h3 class="steps__name">{caps(s["title"])}</h3>',
              f'    <p class="steps__detail">{esc(s["detail"])}{aside}</p>',
              '  </li>']
    o.append('</ol>')
    return o


def lists(ls):
    o = []
    for i, l in enumerate(ls):
        hid = "menu-list-%d" % i
        o += ['<section class="group" aria-labelledby="%s">' % hid,
              '  <header class="group__head">',
              f'    <h3 class="group__title" id="{hid}">{caps(l["title"], 0.05)}</h3>']
        if l.get("note"):
            o.append(f'    <p class="group__note">{esc(l["note"])}</p>')
        if l.get("price") is not None:
            o.append(f'    <p class="group__price">{money(l["price"])}</p>')
        o.append('  </header>')

        if l["layout"] == "priced":
            o.append('  <ul class="priced">')
            for it in l["items"]:
                o += ['    <li class="priced__row">',
                      f'      <span class="priced__name">{esc(it["name"])}</span>',
                      '      <span class="priced__rule" aria-hidden="true"></span>',
                      f'      <span class="priced__price">+{money(it["price"])}</span>',
                      '    </li>']
            o.append('  </ul>')
        elif l["layout"] == "named":
            o.append('  <ul class="named">')
            for it in l["items"]:
                o += ['    <li class="named__item">',
                      f'      <span class="named__name">{caps(it["name"])}</span>',
                      f'      <span class="named__detail">{esc(it["detail"])}</span>',
                      '    </li>']
            o.append('  </ul>')
        else:
            o.append('  <ul class="cols">')
            for it in l["items"]:
                o.append(f'    <li>{esc(it)}</li>')
            o.append('  </ul>')
        o.append('</section>')
    return o


def build(d):
    o = ['<section class="menu" id="menu" aria-labelledby="menu-bowls">',
         '  <div class="menu__inner">']
    o += ["    " + x for x in bowls(d["houseBowls"])]
    o.append('    <hr class="menu__rule">')
    o += ["    " + x for x in byo(d["buildYourOwn"])]
    o += ["    " + x for x in lists(d["lists"])]
    if d.get("footnotes"):
        o.append('    <footer class="menu__foot">')
        for f in d["footnotes"]:
            o.append(f'      <p>{esc(f)}</p>')
        o.append('    </footer>')
    o += ['  </div>', '</section>']
    return "\n".join(o)


def order_cta():
    """The ordering button. A real link once ORDER_URL is set; until then a
    disabled button, which is honest to a screen reader and cannot be
    followed anywhere."""
    if ORDER_URL:
        return (f'    <a class="order__cta" href="{esc(ORDER_URL)}" '
                f'target="_blank" rel="noopener">Order Online</a>')
    WARNINGS.append("ORDER_URL is unset — the ordering button renders disabled. "
                    "Set it in tools/build-menu.py when ChowNow is live.")
    return ('    <button class="order__cta" type="button" disabled>Order Online</button>\n'
            '    <p class="order__note">Online ordering opens soon.</p>')


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    s = INDEX.read_text(encoding="utf-8")

    assert s.count(START) == 1, f"expected exactly one {START}"
    assert s.count(END) == 1, f"expected exactly one {END}"

    block = build(d)
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    out, n = pattern.subn(START + "\n" + block + "\n" + END, s)
    assert n == 1, "menu block substitution did not apply"
    assert block in out, "rendered block missing after substitution"

    # the order band: a Midstar title and the call to action
    title = outline("Order online", scripttype.FONT, "scripttype")
    for a, b, body in ((ORDER_START, ORDER_END, title),
                       (CTA_START, CTA_END, order_cta())):
        assert out.count(a) == 1 and out.count(b) == 1, f"{a} markers missing"
        out, k = re.subn(re.escape(a) + r".*?" + re.escape(b),
                         lambda _: a + "\n" + body + "\n" + b, out, flags=re.S)
        assert k == 1 and body in out, f"{a} substitution did not apply"

    INDEX.write_text(out, encoding="utf-8")

    bowls_n = len(d["houseBowls"]["items"])
    items_n = sum(len(l["items"]) for l in d["lists"])
    print(f"menu rendered: {bowls_n} bowls, {len(d['buildYourOwn']['steps'])} steps, "
          f"{items_n} list items across {len(d['lists'])} lists")

    # Print every build. These are open questions about the client's own data;
    # silence would let them ship unnoticed.
    if WARNINGS:
        print("\nFONT:")
        for w in WARNINGS:
            print(f"  ! {w}")

    if d.get("_unresolved"):
        print("\nUNRESOLVED — needs the client:")
        for q in d["_unresolved"]:
            print(f"  * {q}")


if __name__ == "__main__":
    sys.exit(main())
