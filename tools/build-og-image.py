#!/usr/bin/env python3
"""
Fields — Open Graph share card.

    python3 tools/build-og-image.py

Writes site/assets/img/og-image.jpg at 1200x630, the size Facebook, LinkedIn,
Slack, iMessage and X all expect.

It is deliberately NOT the hero poster. A bare frame of grass says nothing in a
feed — a share card has about a quarter of a second to identify the brand, so
it carries the lockup and the message, composited over the same graded frame
and scrim the site uses.

Type runs larger than the site's proportions because a card is usually rendered
around 500px wide in a timeline, far smaller than it is authored.
"""

import pathlib
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT = ROOT / "source/fonts/Fredoka[wdth,wght].ttf"
LOGO = ROOT / "site/assets/img/fields-primary-brand.svg"
POSTER = ROOT / "site/assets/img/hero-poster.jpg"
OUT = ROOT / "site/assets/img/og-image.jpg"

W, H = 1200, 630
SCRIM = (11, 38, 0)
STRENGTH = 0.25
ALMOND = (244, 233, 225)
SUNSHINE = (249, 225, 77)

TAGLINE = "Good things take thyme."
# The longer line here, unlike the on-campus signage — someone seeing this in a
# feed is not standing in the building.
EYEBROW = "COMING SOON TO CU ANSCHUTZ"


def font_at(size, weight):
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_axes([weight, 100])
    return f


def tracked(draw, xy, text, font, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def tracked_width(draw, text, font, tracking):
    return sum(draw.textlength(c, font=font) for c in text) + tracking * (len(text) - 1)


def background():
    im = Image.open(POSTER).convert("RGB")
    target = W / H
    if im.width / im.height > target:                 # crop to 1.9:1
        nw = int(im.height * target)
        im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
    else:
        nh = int(im.width / target)
        im = im.crop((0, (im.height - nh) // 2, im.width, (im.height + nh) // 2))
    base = im.resize((W, H), Image.LANCZOS).convert("RGBA")

    rad = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(rad)
    cx, cy, rx, ry = W / 2, H * 0.45, W * 0.90, H * 0.70
    for i in range(220, 0, -1):
        f = i / 220
        d.ellipse([cx - rx * f, cy - ry * f, cx + rx * f, cy + ry * f],
                  fill=255 - int(255 * STRENGTH * 0.9 * f * f))
    rad = Image.eval(rad, lambda v: 255 - v)
    base = Image.alpha_composite(base, Image.merge(
        "RGBA", (*[Image.new("L", (W, H), c) for c in SCRIM], rad)))

    lin = Image.new("L", (W, H))
    ld = ImageDraw.Draw(lin)
    for y in range(H):
        t = y / H
        a = (STRENGTH * (0.7 + (0.25 - 0.7) * (t / 0.4)) if t < 0.4
             else STRENGTH * (0.25 + (0.85 - 0.25) * ((t - 0.4) / 0.6)))
        ld.line([(0, y), (W, y)], fill=int(255 * a))
    return Image.alpha_composite(base, Image.merge(
        "RGBA", (*[Image.new("L", (W, H), c) for c in SCRIM], lin)))


def main():
    with tempfile.TemporaryDirectory() as td:
        logo_png = pathlib.Path(td) / "logo.png"
        logo_w = int(W * 0.46)
        subprocess.run(["rsvg-convert", "-w", str(logo_w), "-o", str(logo_png), str(LOGO)],
                       check=True)
        logo = Image.open(logo_png).convert("RGBA")

    card = background()
    draw = ImageDraw.Draw(card)

    tag_size, eye_size = int(W * 0.030), int(W * 0.0185)
    gap_logo, gap_eye = int(W * 0.028), int(W * 0.016)
    tag_font, eye_font = font_at(tag_size, 300), font_at(eye_size, 500)
    tracking = eye_size * 0.32

    block = logo.height + gap_logo + tag_size + gap_eye + eye_size
    top = int(H * 0.5 - block * 0.54)

    card.alpha_composite(logo, ((W - logo.width) // 2, top))
    y = top + logo.height + gap_logo
    tw = draw.textlength(TAGLINE, font=tag_font)
    draw.text(((W - tw) / 2, y), TAGLINE, font=tag_font, fill=ALMOND)
    y += tag_size + gap_eye
    ew = tracked_width(draw, EYEBROW, eye_font, tracking)
    tracked(draw, ((W - ew) / 2 - tracking / 2, y), EYEBROW, eye_font, SUNSHINE, tracking)

    widest = max(logo.width, tw, ew)
    if widest > W * 0.88:
        print(f"  ! content {widest:.0f}px is tight in a {W}px card")

    card.convert("RGB").save(OUT, quality=88, optimize=True, progressive=True)
    print(f"  {OUT.relative_to(ROOT)}  {W}x{H}  {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
