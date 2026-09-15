# Fields — website

Lives entirely inside this folder. Nothing here touches the packaging,
signage, or logo-exploration folders alongside it.

```
website/
├── site/              ← the deployable site. This folder is what gets uploaded.
│   ├── index.html
│   └── assets/{css,js,img,video,fonts}
├── source/            ← masters. Big, uncompressed, NEVER deployed.
│   ├── video/         ← drop camera / editor exports here
│   ├── photography/
│   ├── logo/
│   └── fonts/
├── tools/             ← build scripts (run as `bash`/`python3 tools/…` —
│   │                     Tresorit drops the executable bit on sync)
│   ├── encode-hero-video.sh
│   └── build-logo.py
└── docs/
    ├── video-prep.md  ← how to prep the hero clip, and why
    └── palette.md     ← brand colours + how the page uses them
```

The `source/` ÷ `site/` split is the important part: masters go in one, the
optimised web copies come out into the other. Anything in `site/` should be
reproducible from `source/` by running something in `tools/`.

## Drop new files here

| What you have | Where it goes |
|---|---|
| Hero video from a camera or editor | `source/video/` |
| Food / space photography | `source/photography/` |
| Logo files (AI, EPS, SVG, layered PSD) | `source/logo/` → `python3 tools/build-logo.py` |
| Licensed webfonts | `source/fonts/` — **gitignored**, see below |

Then run the matching script in `tools/` — don't copy files into `site/`
by hand.

## Live review link

**https://based-chase-94.github.io/fields-website/**

Pushing to `main` redeploys it — `.github/workflows/pages.yml` publishes the
`site/` folder, so `source/`, `tools/` and `docs/` stay in the repo but never
reach the web root.

This is a **review deployment, not the live site**: it carries
`<meta name="robots" content="noindex, nofollow">` and a blanket-disallow
`robots.txt` so an unannounced location doesn't turn up in search. Drop both
when it moves to the real domain.

The repo is public, which is what GitHub Pages needs on a free plan. The page
is therefore reachable by anyone with the URL — it isn't secret, just
unlisted.

## Preview it locally

```bash
cd website/site && python3 -m http.server 8080
```

Then <http://localhost:8080>. (Open `index.html` directly and the browser will
block the video and the stylesheet — it needs to be served over HTTP.)

## Current state

- [x] Landing page shell: full-bleed video background, logo, coming-soon text
- [x] Video encode pipeline — see [docs/video-prep.md](docs/video-prep.md)
- [x] **Real vector logo** in place — white, inline SVG, driven by one CSS line
- [x] Favicon cut from the "F" swash (SVG + iOS PNG)
- [x] Brand palette wired to the guidelines (p.12) — see [docs/palette.md](docs/palette.md)
- [x] **Hero video** — grass clip encoded to an 8.8s seamless loop,
      3.6 MB / 1.5 MB. See [docs/video-prep.md](docs/video-prep.md) for the
      recipe and why each part of it is there.
- [ ] **"Heart of the Land"** — the brand display face, licensed from a small
      foundry, awaiting delivery from the studio. Drop the files in
      `source/fonts/`, self-host into `site/assets/fonts/`, and point
      `--display` at it. Jost carries everything until then, per the client.
- [ ] Opening details: timing, email capture, socials
- [x] Hosting — GitHub Pages, auto-deploys from `main`
- [ ] Real domain, and drop the noindex when it goes live

## Logo

`source/logo/Fields Primary Logo.svg` is the master — the retro script
wordmark with `GRAINS + GREENS` beneath, on a 2:1 artboard. The padding inside
its viewBox is the logo's clearspace, so nothing in the build touches the
geometry.

`python3 tools/build-logo.py` strips the Inkscape metadata and the hard-coded
black, then emits:

| Output | Notes |
|---|---|
| `site/index.html` inline `<svg>` | The one the page uses. Filled with `currentColor`, so `--logo-ink` in the stylesheet recolours it — white today, one line to change |
| `fields-primary-white.svg` | Standalone, for email/social/decks |
| `fields-primary-forest.svg` | Same, for light grounds |
| `favicon.svg` | The "F" and its swash knocked out of Forest — the only part that reads at 32 px |
| `apple-touch-icon.png` | 180 px raster, because iOS won't take the SVG |

It's inlined rather than linked because the logo *is* the page: inlining drops
a render-blocking request on a page whose whole job is fast first paint, and
lets CSS own the colour.

The PNG step needs a rasteriser. Without one the script says so and skips it
rather than shipping a stale icon:

```bash
brew install librsvg
```

The earlier lettuce-mark lockup I'd extracted from the print signage has been
removed — this supersedes it. The signage PDFs themselves are untouched in
`../Coming Soon Print  Signage/`.

## A licensing note on the display font

`source/fonts/` is gitignored, and that's deliberate. Self-hosting a webfont
means serving the font file from a public repo, which for most small-foundry
licences counts as redistribution. When "Heart of the Land" arrives, check what
its licence allows before it goes anywhere near this repo — a webfont licence
is usually separate from a desktop one, and may be pageview-limited.

If it can't be self-hosted, the display face can stay a licensed desktop font
used to set the logo and any headline artwork, with Jost carrying live text.
