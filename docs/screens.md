# In-store menu boards (`site/screens/`)

The three TVs in the store each have a XOGO Mini that plays a URL asset. The
URL is a page here that draws the board live: the grass loop as a background
video, the menu on top. It replaces the baked 4K videos from fields-digital-menu,
so a menu change is a JSON edit and a push, not a re-bake and a hand-off.

| Board | TV | URL |
|---|---|---|
| House Bowls | left | `https://fieldsbowls.com/screens/7upeczte/house-bowls/` |
| Grow Your Own | centre | not built yet |
| Proteins + Upgrades | right | not built yet |

`7upeczte` is just an unlisted path segment. It isn't a secret (this repo is
public): `X-Robots-Tag: noindex` in `site/_headers` and the robots meta tag keep the
pages out of search. They aren't in `sitemap.xml`, and deliberately not in
`robots.txt` either: a `Disallow` would advertise the path and hide the noindex
from crawlers. To change the code: `CODE` in `tools/build-screens.py`, the
`/screens/<code>/*` block in `site/_headers`, and the URLs in XOGO.

## Changing the menu

1. Edit `source/menu/menu.json`. The website menu reads the same file.
   - `boardLines` are each description's lines on the board (we break lines by
     hand, as Figma does). They must spell out `ingredients` exactly: the build
     stops if they don't.
   - `boardKicker` is the top-right line, `note` the footer.
2. `python3 tools/build-screens.py` (and `python3 tools/build-menu.py` for the website).
   The build stops if a line runs out of its column.
3. Commit and push to `main`. Cloudflare deploys in about a minute. Each TV checks
   for a new build every 2 minutes and reloads at the loop's seam, so the change is
   on screen within about 3 minutes. Nobody touches XOGO.

## What the page does

- **Layout:** a fixed 3840×2160 stage with Figma's numbers (fields-digital-menu's
  `tools/build-grass-latest.py`, frame "FINAL - 1"), scaled to whatever the
  player's browser reports.
- **Lettering:** Midstar and Heart of the Land are licensed and can't be served,
  so they ship as SVG outlines (`tools/scripttype.py`). The build lays the board out
  with the real fonts in headless Chromium (`tools/screens-measure.mjs`) and puts
  each outline exactly where the text was. Fredoka (OFL) is a self-hosted webfont.
- **Vertical metrics:** every face is pinned to its hhea metrics with
  `ascent-override`/`descent-override`. Chromium on Linux/Android otherwise uses
  Midstar's OS/2 typo metrics, which moves the title about 100 px. The boards were
  matched to Figma on a Mac (hhea), so this keeps every player identical to that.
- **Background:** `source/video/screens/<board>-1080.mp4` (default, about 14 MB) and
  `-2160.mp4` (`?video=4k`, about 22 MB), from `bash tools/encode-screen-loops.sh`.
  Same look as the TV masters (brightness 0.85, blur σ3, frame-exact crossfaded
  loop), no text, each rotated to start at its board's moment. Cloudflare caps a
  static file at 25 MiB; the build refuses anything bigger. The still
  (`source/screens/grass-<board>.jpg`) sits underneath, so a video that fails
  never leaves a black screen.
- **Updates:** `site/screens/<code>/version.json` holds the build id. The page polls
  it (no-store), fetches the new page to be sure it's complete, then reloads when
  the loop wraps. It also reloads itself at 4 AM daily.
- **Offline:** `sw.js` precaches the pages, font, stills and loops. Pages are
  network-first (4 s timeout), assets cache-first, with byte ranges answered from
  the cache so video keeps playing. A small dot bottom-right is faint green
  online, amber when running from cache.
- **Caching:** HTML, `version.json` and `sw.js` are `no-cache`. Everything in
  `site/screens/assets/` has a content hash in its name and is immutable for a year.

## Testing on a TV

- `?check` shows the build id, the player's real screen and viewport size, which
  loop is playing, whether the offline cache is active, and the 5% title-safe
  margin. (The Figma design runs past that margin by design; if a TV crops the
  edges, set its picture size to "Fit to screen".)
- `?video=4k` plays the 4K loop; `?video=off` shows the still only.

## Building

Needs `source/fonts/` (Midstar.otf, Heart-of-the-Land-Regular.otf,
Fredoka-VariableFont_wdth,wght.ttf; gitignored), `source/video/grass.mp4` for new
loops (gitignored), `pip install fonttools uharfbuzz brotli`, ffmpeg, and Node
with Playwright (`npm i -g playwright && npx playwright install chromium`).
