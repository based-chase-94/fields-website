# Menu

```bash
python3 tools/build-menu.py
```

Renders `source/menu/menu.json` into `site/index.html` between the menu markers.

## Why it is static markup

A menu is the page's actual content, so it is written into the HTML at build
time rather than assembled by JavaScript in the browser. It has to be in the
markup for search engines, for screen readers, and for anyone whose JS fails.
A client-side render would buy nothing here.

## The source data

`source/menu/menu.json` is a cleaned copy of the client's recipe cards, which
are kitchen documents — quantities, yields, sub-recipes and internal `[note:]`
lines are stripped. It carries its own `_unresolved` list, printed every time
the build runs, so open questions stay visible rather than being forgotten.

## Colour, and why Poppy is not in it

Almond ground, Forest ink. The hero is dark because it sits over video; a menu
is a wall of text, and long reading wants dark-on-light.

**Poppy is the dominant colour on the digital boards but it measures ~3.2:1 on
Almond** — fine for large display type, well under the 4.5:1 floor for anything
body-sized. Prices use Burgundy (9.7:1) and the step markers are Forest
(10.7:1). Poppy is kept for large headings only.

Muted labels use `--forest-muted`, a fixed colour, not an opacity. The first
pass used opacity and three labels landed between 3.5:1 and 4.3:1. A token gets
measured once; an opacity silently re-derives itself against whatever
background it ends up over.

Every text element in the section was measured against its real composited
background. Worst case is 5.15:1.

## No photography

Structure does the work the pictures would: generous space, one hierarchy, and
prices on a shared right edge so a column can be scanned rather than hunted
through. When food photography arrives, the bowl cards are the natural place
for it.
