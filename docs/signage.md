# On-site signage video

Self-contained looping MP4s for screens in the physical space. Everything is
burned into the pixels — grass, scrim, lockup, coming-soon line — because there
is no browser doing the compositing.

```bash
python3 tools/build-signage.py            # 1920x1080
python3 tools/build-signage.py --portrait # 1080x1920
```

Output lands in `signage/` (gitignored — rebuildable, and tens of megabytes).

## Web grade vs screen grade

Worth being precise, because the two are often confused: **the colour grade is
baked into the video file** by ffmpeg — brightness, saturation and contrast
genuinely change the pixels. **The scrim is an overlay** the page paints on
top in CSS, and it is what makes the type legible.

So handing anyone the web MP4 would give them a noticeably brighter, flatter
picture with no logo and no message. The signage build composites the scrim and
the type into the frames instead.

## Where the defaults deliberately differ from the web build

| | Web | Signage | Why |
|---|---|---|---|
| Quality | CRF 35 | CRF 18 | No download cost. ~26 Mbps, ~98 MB for 31s |
| Softening blur | σ0.6 | none | The blur exists to shrink the web file. On a 55" panel it reads as out of focus |
| Loop length | 8.8s | 31s | Every web second costs bandwidth. On a screen people walk past, a short loop reads as a glitch |
| Frame rate | 24 | 30 | Signage players and panels are happier at 30 |
| Type size | reading distance | viewing distance | The eyebrow lands near 32px of cap height — above the ~24px floor for a 55" panel at ~10ft |
| Entrance | blur-in, staggered | none | People glance at signage. An entrance replaying every loop means catching it mid-fade and missing the message |
| Audio | stripped | silent AAC track | Some players error on a video with no audio stream at all |

Content sits inside a 5% title-safe margin, since panels still overscan. The
build warns if anything lands outside it.

## Loop quality

The seam is crossfaded as on the web. Measured on the 1920x1080 render, the
last-to-first frame difference is **0.36** against an average adjacent-frame
difference of **1.78** — the join is less visible than an ordinary frame step.

## Before sending it to the client's AV contact

Five things worth confirming, because they change the render:

1. **Orientation and resolution.** Landscape and portrait 1080 are both built.
   4K panels would want `--width 3840 --height 2160`.
2. **How it plays.** A USB stick in a TV, or a signage CMS (BrightSign, Samsung
   MagicInfo, LG webOS, Chrome device)? Some CMSes want a specific container or
   a maximum bitrate.
3. **Does the player loop on its own**, or does it need a long file padded to
   a fixed slot length?
4. **Is it sharing a rotation** with other content? If it gets, say, a 15s slot,
   the loop should be cut to match rather than being truncated mid-clip.
5. **Bitrate ceiling.** 26 Mbps is fine for modern hardware. If their player
   stutters, re-run with `--crf 22` — rebuild from the master rather than
   re-compressing the delivered file, which would add a second generation of
   loss for no reason.

## If the message changes

The text lives at the top of `tools/build-signage.py` (`TAGLINE`, `EYEBROW`).
There is deliberately no address, per the client.
