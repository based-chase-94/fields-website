# On-site signage video

Self-contained looping MP4s for screens in the physical space. Everything is
burned into the pixels — grass, scrim, lockup, coming-soon line — because there
is no browser doing the compositing.

```bash
python3 tools/build-signage.py                          # 1920x1080
python3 tools/build-signage.py --portrait               # 1080x1920
python3 tools/build-signage.py --width 3840 --height 2160   # 4K
```

| Render | Bitrate | Size | H.264 level |
|---|---|---|---|
| 3840x2160 | 51 Mbps | 190 MB | 5.1 |
| 1920x1080 | 27 Mbps | 98 MB | 4.2 |
| 1080x1920 | 18 Mbps | 67 MB | 4.2 |

**The level is picked from the resolution, and it matters.** H.264 level 4.2
does not cover 3840x2160; a 4K file tagged 4.2 is out of spec and strict
players and CMS validators reject it outright. Above 1080p the build tags 5.1.

CRF also steps back one notch at 4K (20 rather than 18). At four times the
pixels, CRF 18 lands near 70 Mbps, which is past what a lot of signage hardware
will decode reliably.

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

The signage line reads just **"Coming Soon"**, not "Coming Soon to CU Anschutz"
like the website. These screens are *on* the Anschutz campus, so naming it
there is redundant. The website keeps the longer line, because its visitors
are not standing in the building.

Dropping fifteen characters left the line with no width to hold its place under
the lockup, so it also gained size (0.0165 to 0.0225 of frame width) and
tracking (0.32em to 0.42em). Short all-caps lines carry more tracking
gracefully than long ones do.

There is deliberately no address.
