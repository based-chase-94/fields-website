#!/usr/bin/env python3
"""
Fields — on-site digital signage render.

    python3 tools/build-signage.py                       # 1920x1080
    python3 tools/build-signage.py --portrait            # 1080x1920
    python3 tools/build-signage.py --width 3840 --height 2160

Produces a self-contained looping MP4 for screens in the physical space: the
grass, the scrim, the lockup and the coming-soon line all burned into the
pixels. Nothing is overlaid at playback, because there is no browser involved.

This is a different job from the web hero, and the defaults differ accordingly:

  * No bandwidth ceiling, so quality goes up — CRF 18 instead of 35, and the
    softening blur the web version needs for file size is dropped entirely.
    On a 55" panel that blur would be visible.
  * A much longer loop. The web clip is 8.8s because every second costs
    download; on a screen people walk past, a short loop reads as a glitch.
    The default uses the whole source.
  * Type is sized for viewing distance, not for a laptop, and sits inside a
    title-safe margin because panels still overscan.
  * The text does not animate. People glance at signage — an entrance that
    replays every loop means catching it mid-fade and missing the message.
  * No address, per the client.
"""

import argparse
import pathlib
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT = ROOT / "source/fonts/Fredoka[wdth,wght].ttf"
LOGO = ROOT / "site/assets/img/fields-primary-brand.svg"
SRC = ROOT / "source/video/lush-green-grass-blowing-in-wind.mp4"
OUT = ROOT / "signage"

SCRIM = (11, 38, 0)
ALMOND = (244, 233, 225)
SUNSHINE = (249, 225, 77)

TAGLINE = "Good things take thyme."
EYEBROW = "COMING SOON TO CU ANSCHUTZ"


def sh(cmd):
    subprocess.run(cmd, check=True)


def font_at(size, weight):
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_axes([weight, 100])       # [wght, wdth]
    return f


def tracked_width(draw, text, font, tracking):
    return sum(draw.textlength(ch, font=font) for ch in text) + tracking * (len(text) - 1)


def draw_tracked(draw, xy, text, font, fill, tracking):
    """PIL has no letter-spacing, so step the pen manually."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def scrim_layer(w, h, strength):
    """The page's radial + linear scrim, rasterised."""
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    rad = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(rad)
    cx, cy = w / 2, h * 0.45
    rx, ry = w * 0.90, h * 0.70
    steps = 260
    for i in range(steps, 0, -1):
        f = i / steps
        d.ellipse([cx - rx * f, cy - ry * f, cx + rx * f, cy + ry * f],
                  fill=255 - int(255 * strength * 0.9 * f * f))
    rad = Image.eval(rad, lambda v: 255 - v)
    out = Image.alpha_composite(out, Image.merge(
        "RGBA", (*[Image.new("L", (w, h), c) for c in SCRIM], rad)))

    lin = Image.new("L", (w, h))
    ld = ImageDraw.Draw(lin)
    for y in range(h):
        t = y / h
        a = (strength * (0.7 + (0.25 - 0.7) * (t / 0.4)) if t < 0.4
             else strength * (0.25 + (0.85 - 0.25) * ((t - 0.4) / 0.6)))
        ld.line([(0, y), (w, y)], fill=int(255 * a))
    return Image.alpha_composite(out, Image.merge(
        "RGBA", (*[Image.new("L", (w, h), c) for c in SCRIM], lin)))


def build_overlay(w, h, strength, tmp):
    portrait = h > w
    base = min(w, h) if portrait else w

    # Proportions are tuned for viewing distance. On a 55" 1080p panel at ~10ft
    # the eyebrow lands near 32px of cap height, comfortably above the ~24px
    # legibility floor for that distance.
    logo_w = int(base * (0.72 if portrait else 0.40))
    tag_size = int(base * (0.048 if portrait else 0.027))
    eye_size = int(base * (0.030 if portrait else 0.0165))
    gap_logo = int(base * (0.055 if portrait else 0.032))
    gap_eye = int(base * (0.030 if portrait else 0.018))

    logo_png = tmp / "logo.png"
    sh(["rsvg-convert", "-w", str(logo_w), "-o", str(logo_png), str(LOGO)])
    logo = Image.open(logo_png).convert("RGBA")

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    tag_font = font_at(tag_size, 300)
    eye_font = font_at(eye_size, 500)
    tracking = eye_size * 0.32

    tag_w = draw.textlength(TAGLINE, font=tag_font)
    eye_w = tracked_width(draw, EYEBROW, eye_font, tracking)

    block_h = logo.height + gap_logo + tag_size + gap_eye + eye_size
    top = int(h * 0.5 - block_h * 0.52)

    layer.alpha_composite(logo, ((w - logo.width) // 2, top))
    y = top + logo.height + gap_logo
    draw.text(((w - tag_w) / 2, y), TAGLINE, font=tag_font, fill=ALMOND)
    y += tag_size + gap_eye
    # tracking pads the right side, so shift left by half to stay optically centred
    draw_tracked(draw, ((w - eye_w) / 2 - tracking / 2, y), EYEBROW, eye_font,
                 SUNSHINE, tracking)

    # title-safe check: panels overscan, so nothing may sit outside 90%
    margin = 0.05
    widest = max(logo.width, tag_w, eye_w)
    if widest > w * (1 - 2 * margin):
        print(f"  ! content is {widest:.0f}px wide inside a {w}px frame — "
              f"outside the title-safe area", file=sys.stderr)

    glow = layer.filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(base * 0.006))
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow.putalpha(glow.getchannel("A").point(lambda v: int(v * 0.45)))

    out = Image.alpha_composite(scrim_layer(w, h, strength), shadow)
    return Image.alpha_composite(out, layer)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--portrait", action="store_true")
    ap.add_argument("--speed", type=float, default=0.6)
    ap.add_argument("--take", type=float, default=0)          # 0 = whole source
    ap.add_argument("--xfade", type=float, default=1.5)
    ap.add_argument("--fps", type=int, default=30)            # signage players prefer 30
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--scrim", type=float, default=0.25)
    ap.add_argument("--name", default="fields-signage")
    a = ap.parse_args()

    w, h = (1080, 1920) if a.portrait else (a.width, a.height)
    OUT.mkdir(exist_ok=True)

    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(SRC)], capture_output=True, text=True).stdout)
    take = a.take or dur
    T = take / a.speed

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        print(f"── overlay ─── {w}x{h}")
        build_overlay(w, h, a.scrim, tmp).save(tmp / "overlay.png")

        # Grade matches the site exactly. hqdn3d stays (it helps the encoder);
        # the web build's gblur does not — at this bitrate it only costs sharpness.
        chain = (f"setpts=PTS/{a.speed},fps={a.fps},hqdn3d=2:1:4:3,"
                 f"eq=brightness=0.07:saturation=1.32:contrast=1.24,"
                 f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,"
                 f"crop={w}:{h},format=yuv420p")
        print("── grade + reframe ───")
        sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y",
            "-t", str(take), "-i", str(SRC), "-an",
            "-vf", chain, "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "12", str(tmp / "graded.mp4")])

        L = T - a.xfade
        print(f"── loop seam ─── crossfading {a.xfade}s, {T:.1f}s -> {L:.1f}s")
        sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y",
            "-i", str(tmp / "graded.mp4"), "-an", "-filter_complex",
            f"[0:v]split=3[a][b][c];"
            f"[a]trim=start={L},setpts=PTS-STARTPTS[tail];"
            f"[b]trim=start=0:end={a.xfade},setpts=PTS-STARTPTS[head];"
            f"[c]trim=start={a.xfade}:end={L},setpts=PTS-STARTPTS[body];"
            f"[tail][head]xfade=transition=fade:duration={a.xfade}:offset=0[x];"
            f"[x][body]concat=n=2:v=1:a=0[v]",
            "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "12", str(tmp / "looped.mp4")])

        out = OUT / f"{a.name}-{w}x{h}.mp4"
        print("── burn in + encode ───")
        sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y",
            "-i", str(tmp / "looped.mp4"), "-i", str(tmp / "overlay.png"),
            "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p",
            # A silent track: some signage players error on a video with no audio.
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-shortest",
            "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.2",
            "-preset", "slow", "-crf", str(a.crf),
            "-x264-params", f"keyint={a.fps*2}:min-keyint={a.fps*2}:scenecut=0",
            "-c:a", "aac", "-b:a", "96k",
            "-movflags", "+faststart", str(out)])

        poster = OUT / f"{a.name}-{w}x{h}-still.jpg"
        sh(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "2",
            "-i", str(out), "-frames:v", "1", "-q:v", "2", str(poster)])

    mb = out.stat().st_size / 1048576
    print(f"\n  {out.relative_to(ROOT)}  {mb:.1f} MB  ({L:.1f}s loop, {a.fps}fps)")
    print(f"  {poster.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
