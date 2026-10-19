# Menu

The menu is data, not markup. `source/menu/menu.json` is the source of truth;
`tools/build-menu.py` renders it into `site/index.html` between:

```
<!-- menu:start -->
<!-- menu:end -->
```

Edit the JSON, then:

```bash
python3 tools/build-menu.py
python3 tools/stamp-assets.py   # only if you also touched CSS or JS
```

## Why build-time, not client-side

The menu is the page's actual content. It has to be in the markup for search
engines, for screen readers, and for anyone whose JS fails. A client-side
render would buy nothing and cost all three.

## Shapes

Three list layouts cover everything:

- `"layout": "columns"` — plain names, flowed into CSS columns.
- `"layout": "priced"` — name, leader rule, figure.
- `"layout": "named"` — name over a description, with one `price` on the
  group rather than per item. Drinks use this.

Bowls are their own shape: name, price, and an ingredient string.

`footnotes` closes the section with quiet sourcing notes.

## Colour

The menu sits on `--page` (`#F6EAE1`), not on Forest. That matters:

| Colour | On `#F6EAE1` | Usable for text |
|---|---|---|
| Forest `#283628` | 10.8:1 | yes |
| Burgundy `#5F2637` | 9.8:1 | yes — prices use it |
| `--ink-muted` `#5c6457` | 5.2:1 | yes |
| Poppy `#E84A28` | 3.3:1 | large only |
| **Sunshine `#F9E14D`** | **1.12:1** | **no** |

Sunshine is the brand's signature and the digital boards set prices in it. On
this background it is invisible. It appears in the menu only as a *fill* behind
dark ink — the step number pills, where Forest on Sunshine measures 9.7:1.

Do not set menu text in Sunshine. Check any new colour against `--page` before
using it.

## Open questions

`_unresolved` in the JSON holds questions about the client's own data. The
build prints them every run — that is deliberate. They are not rendered to the
page.

## Section titles are Midstar outlines

`House Bowls` and `Build Your Own` are set in Midstar and rendered to SVG
paths at build time by `tools/scripttype.py`. The font file never ships.

Midstar is licensed from Subectype and its own embedded metadata says:

> You can not resell, share or giveaway the font files

Serving a webfont hands the file to every visitor, and this repo is public, so
self-hosting is out on both counts. Outlines are how the wordmark already
works — the shapes travel, the font does not.

Put `Midstar.otf` in `source/fonts/` (already gitignored). Build-time tools:

```bash
python3 -m pip install --user fonttools uharfbuzz
```

Text is shaped with HarfBuzz, not by stacking advance widths — Midstar carries
a `kern` feature and `liga` substitutions.

Without the font the build still succeeds: titles fall back to plain text and
the build prints a `FONT:` warning. Check for that line before shipping.

## All-caps lines are Heart of the Land

Everything in the menu that was uppercase Fredoka — bowl names, step names,
group titles, refresher names — is set in Heart of the Land outlines. 21
drawings in all. Both display faces are rendered rather than served; see the
licence note above and in `tools/scripttype.py`.

Two consequences worth knowing:

**The words stay in the markup.** `scripttype.replace()` emits the real text
in a visually-hidden span and marks the drawing `aria-hidden`. `render()`
alone puts the words only in an `aria-label`, which screen readers announce
but crawlers do not index — fine for a section title, a mistake for
"Strawberry Fields", which is exactly the phrase someone searches. Check that
product names still appear in `site/index.html` after any change here.

**`letter-spacing` and `text-transform` do nothing.** Both are baked at render
time. Tracking is a `tracking=` argument in ems on the call; the face is
unicase, so casing in the JSON is immaterial.

Outlines size from `--sw` / `--sh` custom properties rather than an inline
width, because an inline width cannot be overridden by CSS — the drawings
could not shrink inside a flex row and pushed the page 7px wider than a phone
viewport. The stylesheet turns the ratios into `width` + `aspect-ratio` and
caps them with `max-width: 100%`.
