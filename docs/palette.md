# Palette

From **Fields Brand Guidelines, p.12**. These are the authority — nothing in
the site should carry a colour that isn't on this page. The CSS custom
properties at the top of `site/assets/css/site.css` mirror it one-to-one.

## Primary

| | Name | HEX | RGB | CMYK |
|---|---|---|---|---|
| ⬛ | Forest | `#283628` | 40, 54, 40 | C77 M52 Y80 K65 |
| 🟨 | Sunshine | `#F9E14D` | 249, 225, 77 | C2 M7 Y99 K0 |
| 🟧 | Poppy | `#E84A28` | 232, 74, 40 | C0 M93 Y100 K0 |

## Secondary

| | Name | HEX | RGB | CMYK |
|---|---|---|---|---|
| 🟥 | Burgundy | `#5F2637` | 95, 38, 55 | C40 M94 Y59 K45 |
| 🟩 | Chartreuse | `#B4AA4F` | 180, 170, 79 | C31 M25 Y95 K1 |
| 🟪 | Lavender | `#BEA8D5` | 190, 168, 213 | C21 M35 Y0 K0 |
| ⬜ | Almond | `#F4E9E1` | 244, 233, 225 | C2 M8 Y9 K0 |

## How the landing page uses them

| Role | Token | Colour |
|---|---|---|
| Page ground, veil, still fallback | `--forest` / `--forest-rgb` | Forest |
| Video scrim | `--scrim-rgb` | Deep green `#0B2600` |
| Logo script | `--logo-ink` | Sunshine |
| GRAINS + GREENS | `--logo-sub-ink` | White `#FFFFFF` |
| Tagline | `--ink-on-dark` → `--almond` | Almond |
| "Coming Soon" eyebrow | `--accent` → `--sunshine` | Sunshine |
| Favicon ground | — | Forest |

`--accent` was Chartreuse until the real hero footage went in. Against green
grass an olive-yellow is the same hue family, and it measured **3.9:1** — below
the 4.5:1 floor. Sunshine measures **7.1:1** through the same scrim and is a
primary brand colour, so it took over.

## Contrast

Two sets of numbers matter, and only the second is real.

**Against flat Forest** — what the fallback still and any solid-ground layout
get: Almond 10.7:1, Sunshine 9.7:1, Chartreuse 5.3:1.

**Against the hero video through the scrim** — measured off the composited
frame, which is what a visitor actually sees:

| Element | Colour | Ratio |
|---|---|---|
| Logo script | Sunshine | 7.4:1 |
| GRAINS + GREENS | White | 9.8:1 |
| Tagline | Almond | 8.2:1 |
| "Coming Soon" | Sunshine | 7.4:1 |
| Address | Almond | 8.2:1 |

All of them clear AA for normal text. Re-measure if the hero clip is ever
replaced with brighter footage — a bright clip pushes every one of these down,
and `--scrim-strength` is the knob that pulls them back.

The lockup is two-tone at the client's request: the script in Sunshine, the
GRAINS + GREENS line under it in white. White isn't in the palette but is what
the sub-line is set in; `--logo-sub-ink` changes it if that should move to
Almond.

Sunshine now carries both the logo script and the "Coming Soon" eyebrow. That
is a lot of weight on one accent — if the eyebrow starts to feel like it's
competing with the lockup rather than supporting it, moving it to Almond is a
one-line change to `--accent`.

## Why the scrim isn't Forest

The one place the page deliberately uses a colour that isn't in the guidelines.
Forest is a desaturated green, and compositing it over the hero video bleached
about 12% of the chroma out of the footage. `--scrim-rgb` (`#0B2600`) is a deep
saturated green that darkens just as effectively without that cost — see
[video-prep.md](video-prep.md). It is never seen as a flat colour, only as a
gradient over moving footage; the page ground, the intro veil and the still
fallback are all still Forest.

## Type

Fredoka, variable weight 300-700, in three treatments that mirror what the
page used before it:

| Element | Weight | Treatment |
|---|---|---|
| Tagline | 300 Light | Sentence case, 0.01em |
| "Coming Soon…" | 500 Medium | Uppercase, 0.32em |
| Address | 400 Regular | Sentence case, 0.02em |

The lowercase sizes sit ~5% below their previous values. Fredoka's x-height
measures 7.6% larger than the face it replaced and it sets ~8% wider, so
carrying the old numbers over would have let the supporting text creep up on
the lockup. Uppercase needed no change — cap height differs by only 4%, and
the tracked-out eyebrow actually sets 1.4% *narrower*.

`--display` is aliased to it until "Heart of the Land" is licensed.
