#!/usr/bin/env python3
"""
Fields — menu section.

    python3 tools/build-menu.py

Renders source/menu/menu.json into site/index.html between the menu markers.

Plain semantic HTML, written at build time rather than assembled by JavaScript
in the browser. A menu is the page's actual content: it has to be in the markup
for search engines, for screen readers, and for anyone whose JS fails. There is
nothing here a client-side render would buy.
"""

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "source/menu/menu.json"
INDEX = ROOT / "site/index.html"


def money(v):
    # Always two decimals. "$6" sitting next to "$4.25" in the same column
    # reads as a typo rather than a rounder price.
    return f"${v:,.2f}"


def esc(s):
    return html.escape(str(s), quote=False)


def ul(items, cls="menu__list"):
    li = "".join(f"<li>{esc(i)}</li>" for i in items)
    return f'<ul class="{cls}">{li}</ul>'


def priced(rows):
    li = "".join(
        f'<li><span class="menu__item">{esc(r["name"])}</span>'
        f'<span class="menu__dots" aria-hidden="true"></span>'
        f'<span class="menu__price">{money(r["price"])}</span></li>'
        for r in rows
    )
    return f'<ul class="menu__list menu__list--priced">{li}</ul>'


def build(d):
    byo = d["buildYourOwn"]
    out = []
    out.append('<section class="menu" id="menu" aria-labelledby="menu-heading">')
    out.append('  <div class="menu__inner">')
    out.append(f'    <h2 class="menu__heading" id="menu-heading">The Menu</h2>')

    # ---- build your own -----------------------------------------------------
    out.append('    <div class="menu__block">')
    out.append('      <header class="menu__blockhead">')
    out.append(f'        <h3>{esc(byo["name"])}</h3>')
    out.append(f'        <p class="menu__from">from <strong>{money(byo["price"])}</strong></p>')
    out.append('      </header>')

    fmts = "".join(
        f'<li><span class="menu__item">{esc(f["name"])}</span>'
        f'<span class="menu__detail">{esc(f["detail"])}</span></li>'
        for f in byo["formats"]
    )
    out.append(f'      <ul class="menu__formats">{fmts}</ul>')

    out.append('      <ol class="menu__steps">')
    for s in byo["steps"]:
        out.append('        <li class="menu__step">')
        note = f' <span class="menu__note">{esc(s["note"])}</span>' if s.get("note") else ""
        out.append(f'          <h4><span class="menu__stepnum" aria-hidden="true">{s["n"]}</span>'
                   f'{esc(s["title"])}{note}</h4>')
        if s.get("groups"):
            for g in s["groups"]:
                gnote = f' <span class="menu__note">{esc(g["note"])}</span>' if g.get("note") else ""
                out.append(f'          <h5>{esc(g["label"])}{gnote}</h5>')
                out.append(f'          {ul(g["items"])}')
        if s.get("items"):
            out.append(f'          {ul(s["items"])}')
        if s.get("priced"):
            out.append(f'          {priced(s["priced"])}')
        out.append('        </li>')
    out.append('      </ol>')
    out.append('    </div>')

    # ---- signature bowls ----------------------------------------------------
    out.append('    <div class="menu__block">')
    out.append('      <header class="menu__blockhead"><h3>Signature Bowls</h3></header>')
    out.append('      <div class="menu__bowls">')
    for b in d["signatureBowls"]:
        out.append('        <article class="bowl">')
        out.append('          <h4 class="bowl__name">'
                   f'<span>{esc(b["name"])}</span>'
                   f'<span class="bowl__price">{money(b["price"])}</span></h4>')
        if b.get("formats"):
            out.append(f'          <p class="bowl__formats">{esc(b["formats"])}</p>')
        parts = [b["base"]]
        if b.get("protein"):
            parts.append(b["protein"])
        parts += b["items"]
        out.append(f'          <p class="bowl__body">{esc(" · ".join(parts))}</p>')
        out.append(f'          <p class="bowl__dressing">{esc(b["dressing"])}</p>')
        out.append('        </article>')
    out.append('      </div>')
    out.append('    </div>')

    out.append('    <p class="menu__footnote">Prices and items subject to change before opening.</p>')
    out.append('  </div>')
    out.append('</section>')
    return "\n".join(out)


def main():
    d = json.loads(DATA.read_text())
    block = build(d)
    page = INDEX.read_text()
    new, n = re.subn(
        r"(<!-- menu:start -->).*?(<!-- menu:end -->)",
        lambda m: m.group(1) + "\n" + block + "\n" + m.group(2),
        page, flags=re.S,
    )
    if not n:
        raise SystemExit("index.html is missing the <!-- menu:start/end --> markers")
    INDEX.write_text(new)
    bowls = len(d["signatureBowls"])
    steps = len(d["buildYourOwn"]["steps"])
    print(f"  menu written: {steps} steps, {bowls} signature bowls, {len(block)//1024} KB of markup")
    if d.get("_unresolved"):
        print("\n  still unresolved in the source data:")
        for u in d["_unresolved"]:
            print(f"    · {u}")


if __name__ == "__main__":
    main()
