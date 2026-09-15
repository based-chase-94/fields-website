# Preparing the hero video

Everything here assumes one master file goes in `source/video/`, and
`tools/encode-hero-video.sh` produces everything the site actually serves.
Never hand-drop a camera file into `site/assets/video/`.

---

## What to shoot / choose for

A background video is not a film. It is wallpaper that moves. The clip has to
survive being cropped to an unknown aspect ratio, dimmed ~50%, and having a
logo sit on top of it.

| | Aim for | Why |
|---|---|---|
| **Length** | 8–15 seconds | Past ~15s the file gets heavy and nobody watches that long anyway |
| **Motion** | Slow and continuous — a slow push in, a slow pan, steam rising, hands working | Fast cuts and hard camera moves fight the type and make the loop obvious |
| **Composition** | Keep the centre third calm and uncluttered | That is where the logo and "Coming Soon" sit |
| **Exposure** | Slightly *over* your instinct | The page dims it. A moody clip becomes a black rectangle |
| **Cuts** | Ideally none — one continuous take | Every cut is a spike in file size and a jolt behind static type |
| **Audio** | Irrelevant — it gets stripped | Autoplay only works muted, so the track is dead weight |

**Loop point.** The end should be able to meet the beginning without a visible
jump. Three ways, easiest first:

1. Pick a take where the start and end frames look near-identical (a slow
   orbit that returns, steam, a crowd) and let it hard-cut.
2. Let it hard-cut anyway and make the cut land on a moment of low motion —
   most people never notice.
3. Boomerang it — play forwards then backwards. Reads as artificial on human
   motion, but is invisible on smoke, water, grain pouring, leaves.

---

## The actual answer on file size

Yes, it matters, and it is the single biggest thing that will make this page
feel cheap or expensive.

**Budget: the 1920-wide MP4 should come in under 4 MB. 6 MB is the ceiling.**

Not because of bandwidth cost — because of time-to-first-frame. The poster
image paints in under a second; the video has to arrive before it can replace
it. Over ~6 MB, a visitor on hotel wifi sees a still image for the whole visit.

Size is driven by three things, in this order:

1. **Duration** — linear. Halving the clip halves the file. Cheapest lever.
2. **Motion** — a locked-off shot of steam compresses to a fraction of a
   handheld walk through a room. Nothing you can do at encode time fixes a
   busy shot.
3. **Resolution** — 1920 wide is the right target. 4K is pure waste: it is
   behind a 50% scrim, cropped, and nobody is inspecting it.

If you blow the budget, cut duration first, then accept a softer encode. Don't
drop below 1280 wide.

---

## Background video is not video

The defaults in the encoder are tuned for footage that sits *behind* a scrim
and a logo. Four treatments do most of the work, and none of them cost anything
you can see at that job:

| Treatment | Flag | Why |
|---|---|---|
| **Denoise** | on by default | Sensor grain is random, so it can't be predicted between frames. It is the most expensive thing in the file and the least visible |
| **Gentle blur** | on by default | σ0.6 — takes the hardest edges off foliage, which is exactly where H.264 spends everything. Invisible behind a scrim |
| **24 fps** | `-f` | Saves ~10%. Background motion is slow; nobody reads 30 fps into wallpaper |
| **Slow it down** | `-S 0.6` | The big one. Less change between frames means less to encode — ~30% off at the same output length — and slow motion suits a calm background better anyway |

`-R` turns the denoise and blur off if you ever need the footage sharp.

## Making the loop seamless

Almost no clip loops on its own. The encoder crossfades the tail into the head
(`-x`, default 1 second), which costs that second of length and makes the clip
end on the frame it starts on.

On textured footage — grass, water, foliage, smoke — this is completely
invisible, because there is no structure for the eye to catch the dissolve on.
The grass clip measured **84% of the way to a visible jump** before the
crossfade and **17%** after, where a normal frame-to-frame step is 0%.

## What we actually did with the grass clip

Source: 3840x2160, 19.5s, 75 Mbps, 176 MB.

```bash
bash tools/encode-hero-video.sh -t 6 -S 0.6 -x 1.2 -q 34 -e 0.04 -p 2.5 \
  source/video/lush-green-grass-blowing-in-wind.mp4
```

Six seconds of source, slowed to 0.6x, crossfaded — an 8.8 second loop at
**3.6 MB / 1.5 MB**. Some notes on why those numbers:

- **Six seconds is plenty.** The frame is wall-to-wall grass with no horizon
  and no subject, so one stretch looks exactly like any other. For pure
  texture, loop length is close to irrelevant — nobody can tell 9 seconds from
  20. That is what bought the budget.
- **It needed grading** (`-e 0.07 -a 1.32 -k 1.07`). The footage measures 21%
  mean luminance — much darker than it looks — and reads muted and olive
  ungraded. Saturation past ~1.5 turns the green acid and flattens the
  highlights, so 1.32 is about the ceiling for footage this saturated already.
- **The scrim came *down*, not up.** White type clears 11:1 against the raw
  footage, so the scrim here is about letting the video recede, not legibility.
  It sits at 0.45.

## Grade in the encode, never in CSS

There was a `filter: saturate(0.92) contrast(1.04)` on the video element for a
while. It applied to the `<video>` but **not** to the poster still behind
`.is-still`, so the two states were graded differently — a visitor on
reduced-motion or a failed autoplay saw a different picture from everyone else.

All grading now lives in `-e` / `-a` / `-k`, which bake into the renditions and
the poster alike.

## Watch out: WebM does not always win

The usual advice — ship VP9, it's 25-35% smaller — **is false for dense moving
foliage.** Matched for quality against H.264 on this clip, VP9 came out 30%
larger at 1920 and 72% larger at 1280.

That matters because the page lists WebM first, so a fat WebM means Chrome and
Firefox download *more* than Safari. The encoder now measures both, keeps the
WebM only when it actually wins, and rewrites the `<source>` list in
`index.html` to match what survived. For the grass clip, nothing survived: the
page ships H.264 only.

Don't assume this holds for the next clip. The script re-checks every run.

## Do you need a tool?

`ffmpeg` is already installed on this machine and the script wraps it. That is
the whole toolchain — no Handbrake, no web service, no subscription.

Where a paid tool would help and doesn't here: automatic per-device
renditions and a CDN. For a coming-soon page, four static files are fine.

---

## Running it

```bash
cd website
bash tools/encode-hero-video.sh source/video/fields-hero-master.mov
```

Trim while you encode rather than round-tripping through an editor:

```bash
# start at 4.5s, take 12 seconds of source, pull the poster from 6s into the result
bash tools/encode-hero-video.sh -s 4.5 -t 12 -p 6 source/video/fields-hero-master.mov
```

Note `-t` counts **source** seconds and `-p` counts **output** seconds — they
differ whenever `-S` is in play.

Crop a vertical or square master to something the page can use:

```bash
bash tools/encode-hero-video.sh -c 2160:1215 source/video/phone-clip.mov
```

Over budget? Push quality down (higher number = smaller file). 25 is the
default, 28 is still clean behind a scrim, 31 starts to show banding on
gradients and smoke.

```bash
bash tools/encode-hero-video.sh -q 28 -t 10 source/video/fields-hero-master.mov
```

### What comes out

| File | Used by |
|---|---|
| `hero-1920.mp4` (+ `.webm` if it wins) | Desktop and large tablets |
| `hero-1280.mp4` (+ `.webm` if it wins) | Phones and small windows |
| `hero-poster.jpg` | Paints instantly; also the fallback for reduced-motion, data-saver, and any playback failure |

WebM first, MP4 second where a WebM exists — see the codec warning above.

---

## Checking your work

- Load the page on a phone over cellular, not wifi.
- Watch the loop for a full minute. If you flinch at the seam, re-cut it.
- Squint at it. The logo should stay legible. If it doesn't, raise
  `--scrim-strength` in `site/assets/css/site.css` rather than re-grading
  the footage.
- Confirm the poster frame is a *good* frame. For a meaningful share of
  visitors it is the only thing they'll see.
