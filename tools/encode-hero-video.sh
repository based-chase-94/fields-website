#!/usr/bin/env bash
#
# Fields — hero background video encoder
#
#   bash tools/encode-hero-video.sh source/video/my-clip.mov
#
# Takes one master and emits every variant the landing page needs into
# site/assets/video/, plus a poster frame into site/assets/img/.
#
# The defaults are tuned for *background* video, which is a different job from
# video someone actually watches: it sits behind a scrim and a logo, so detail
# nobody can see is pure file size. See docs/video-prep.md.
#
# Trim / timing
#   -s <sec>   start here                      (default 0)
#   -t <sec>   seconds of SOURCE to take       (default: to the end)
#   -S <n>     playback speed, <1 = slower     (default 1)
#   -f <fps>   output frame rate               (default 24)
#   -x <sec>   crossfade the loop seam         (default 1; 0 = hard cut)
#
# Picture
#   -e <n>     brightness lift, -1..1          (default 0)
#   -a <n>     saturation, 1 = untouched        (default 1)
#   -k <n>     contrast, 1 = untouched          (default 1)
#   -c <w:h>   crop before scaling
#   -p <sec>   poster frame, in OUTPUT time    (default 0)
#   -R         raw: skip the denoise + softening
#
# Output
#   -n <name>  basename                        (default hero)
#   -q <crf>   H.264 quality, higher = smaller (default 30)
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_V="$ROOT/site/assets/video"
OUT_I="$ROOT/site/assets/img"

START=0; TAKE=""; SPEED=1; FPS=24; XFADE=1
LIFT=0; SAT=1; CON=1; CROP=""; POSTER_AT=0; SOFTEN=1
NAME="hero"; CRF=30

while getopts "s:t:S:f:x:e:a:k:c:p:Rn:q:" opt; do
  case "$opt" in
    s) START="$OPTARG" ;;   t) TAKE="$OPTARG" ;;    S) SPEED="$OPTARG" ;;
    f) FPS="$OPTARG" ;;     x) XFADE="$OPTARG" ;;   e) LIFT="$OPTARG" ;;
    a) SAT="$OPTARG" ;;     k) CON="$OPTARG" ;;
    c) CROP="$OPTARG" ;;    p) POSTER_AT="$OPTARG" ;; R) SOFTEN=0 ;;
    n) NAME="$OPTARG" ;;    q) CRF="$OPTARG" ;;
    *) exit 1 ;;
  esac
done
shift $((OPTIND - 1))

SRC="${1:-}"
[ -f "$SRC" ] || { echo "usage: bash $(basename "$0") [options] <source-video>" >&2; exit 1; }

command -v ffmpeg >/dev/null || { echo "ffmpeg not found (brew install ffmpeg)" >&2; exit 1; }
mkdir -p "$OUT_V" "$OUT_I"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

SRC_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC")
[ -n "$TAKE" ] || TAKE=$(echo "$SRC_DUR - $START" | bc)
# Length after the speed change — everything downstream is in output time.
T=$(echo "scale=4; $TAKE / $SPEED" | bc)

echo "── source ─────────────────────────────────────────────"
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate,codec_name \
  -show_entries format=duration,size -of default=nw=1 "$SRC"
echo
printf "take %ss from %ss, at %sx speed -> %ss of footage\n" "$TAKE" "$START" "$SPEED" "$T"

# ---- stage 1: one processed, near-lossless working copy ---------------------
# Everything expensive (4K decode, denoise, resampling) happens once here; the
# renditions below are cheap scales off this.

CHAIN="setpts=PTS/$SPEED,fps=$FPS"
[ -n "$CROP" ] && CHAIN="$CHAIN,crop=$CROP"
if [ "$SOFTEN" = "1" ]; then
  # hqdn3d strips the sensor noise that costs the most bits and shows the
  # least; the blur is deliberately gentle — just enough to take the hardest
  # edges off foliage, which is where H.264 spends everything.
  CHAIN="$CHAIN,hqdn3d=4:3:6:4,gblur=sigma=0.6"
fi
# The grade is baked in here rather than applied as a CSS filter, so the video
# and the poster still are graded identically and the two states match.
if [ "$LIFT" != "0" ] || [ "$SAT" != "1" ] || [ "$CON" != "1" ]; then
  CHAIN="${CHAIN},eq=brightness=${LIFT}:saturation=${SAT}:contrast=${CON}"
fi
CHAIN="$CHAIN,scale='min(1920,iw)':-2:flags=lanczos,format=yuv420p"

echo
echo "── processing ───"
ffmpeg -hide_banner -loglevel error -stats -y -ss "$START" -t "$TAKE" -i "$SRC" \
  -an -sn -dn -vf "$CHAIN" -c:v libx264 -preset veryfast -crf 14 "$WORK/work.mp4"

# ---- stage 2: make the loop seamless ---------------------------------------
# A hard cut back to frame 0 pops on any textured shot. Crossfading the tail
# into the head costs `-x` seconds of length and makes the seam invisible:
# the clip now ends on the same frame it begins on.

LOOPED="$WORK/work.mp4"
if [ "$(echo "$XFADE > 0" | bc)" = "1" ]; then
  L=$(echo "scale=4; $T - $XFADE" | bc)
  if [ "$(echo "$L > $XFADE" | bc)" = "1" ]; then
    echo "── loop seam ───  crossfading ${XFADE}s, ${T}s -> ${L}s"
    ffmpeg -hide_banner -loglevel error -stats -y -i "$WORK/work.mp4" -an \
      -filter_complex "\
        [0:v]split=3[a][b][c];\
        [a]trim=start=$L,setpts=PTS-STARTPTS[tail];\
        [b]trim=start=0:end=$XFADE,setpts=PTS-STARTPTS[head];\
        [c]trim=start=$XFADE:end=$L,setpts=PTS-STARTPTS[body];\
        [tail][head]xfade=transition=fade:duration=$XFADE:offset=0[x];\
        [x][body]concat=n=2:v=1:a=0[v]" \
      -map "[v]" -c:v libx264 -preset veryfast -crf 14 "$WORK/looped.mp4"
    LOOPED="$WORK/looped.mp4"
  else
    echo "── loop seam ───  clip too short to crossfade ${XFADE}s, leaving a hard cut"
  fi
fi

# ---- stage 3: renditions ----------------------------------------------------

h264 () { ffmpeg -hide_banner -loglevel error -stats -y -i "$LOOPED" -an -sn -dn \
  -vf "scale=$1:-2:flags=lanczos,format=yuv420p" \
  -c:v libx264 -profile:v high -level:v 4.1 -preset slow -crf "$2" \
  -x264-params "keyint=$((FPS * 2)):min-keyint=$((FPS * 2)):scenecut=0" \
  -movflags +faststart "$3"; }

vp9 ()  { ffmpeg -hide_banner -loglevel error -stats -y -i "$LOOPED" -an -sn -dn \
  -vf "scale=$1:-2:flags=lanczos,format=yuv420p" \
  -c:v libvpx-vp9 -crf "$2" -b:v 0 -row-mt 1 -deadline good -cpu-used 2 \
  -g $((FPS * 2)) "$3"; }

# VP9's CRF scale runs 0-63 against x264's 0-51, so matching quality needs a
# large offset. The exact crossover is content-dependent — dense moving foliage
# is a case where VP9 barely wins at all — so the sizes get checked below
# rather than assumed.
echo; echo "── 1920w  H.264 ───"; h264 1920 "$CRF"          "$OUT_V/$NAME-1920.mp4"
echo "── 1920w  VP9  ───";        vp9  1920 $((CRF + 13))   "$OUT_V/$NAME-1920.webm"
echo "── 1280w  H.264 ───";       h264 1280 $((CRF + 1))    "$OUT_V/$NAME-1280.mp4"
echo "── 1280w  VP9  ───";        vp9  1280 $((CRF + 14))   "$OUT_V/$NAME-1280.webm"

# The page lists WebM before MP4, so a WebM that came out bigger would make
# Chrome and Firefox download *more* than Safari. Drop any that didn't win and
# take its <source> out of the markup, so nothing 404s at runtime either.
echo
echo "── codec check ───"
for w in 1920 1280; do
  mp4="$OUT_V/$NAME-$w.mp4"; webm="$OUT_V/$NAME-$w.webm"
  [ -f "$webm" ] && [ -f "$mp4" ] || continue
  bm=$(stat -f%z "$mp4"); bw=$(stat -f%z "$webm")
  if [ "$bw" -ge "$bm" ]; then
    pct=$(echo "scale=0; ($bw - $bm) * 100 / $bm" | bc)
    printf "  %sw  WebM is %s%% LARGER than H.264 — dropping it\n" "$w" "$pct"
    rm -f "$webm"
  else
    pct=$(echo "scale=0; ($bm - $bw) * 100 / $bm" | bc)
    printf "  %sw  WebM saves %s%% — keeping\n" "$w" "$pct"
  fi
done

python3 - "$ROOT/site/index.html" "$OUT_V" "$NAME" <<'SYNC'
import pathlib, re, sys
index, out_v, name = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
html = index.read_text()
for width in ("1920", "1280"):
    for ext in ("webm", "mp4"):
        attr = f'data-src-{width}-{ext}'
        line = f'\n    {attr}="assets/video/{name}-{width}.{ext}"'
        html = re.sub(r'\n\s*' + attr + r'="[^"]*"', "", html)
        if (out_v / f"{name}-{width}.{ext}").exists():
            html = html.replace('\n    poster=', line + '\n    poster=', 1)
index.write_text(html)
print("  index.html sources synced to what actually exists")
SYNC

echo "── poster frame ───"
ffmpeg -hide_banner -loglevel error -y -ss "$POSTER_AT" -i "$LOOPED" -frames:v 1 \
  -vf "scale=1920:-2:flags=lanczos" -q:v 4 "$OUT_I/$NAME-poster.jpg"

echo
echo "── results ────────────────────────────────────────────"
total=0
for f in "$OUT_V/$NAME"-1920.mp4 "$OUT_V/$NAME"-1920.webm \
         "$OUT_V/$NAME"-1280.mp4 "$OUT_V/$NAME"-1280.webm \
         "$OUT_I/$NAME-poster.jpg"; do
  [ -f "$f" ] || continue
  b=$(stat -f%z "$f")
  printf "  %-24s %8.2f MB\n" "$(basename "$f")" "$(echo "scale=3;$b/1048576" | bc)"
done
BIG=$(stat -f%z "$OUT_V/$NAME-1920.mp4")
MB=$(echo "scale=2; $BIG/1048576" | bc)
echo
if [ "$(echo "$MB > 4" | bc)" = "1" ]; then
  echo "  ⚠  ${MB} MB at 1920 — over the 4 MB budget."
  echo "     Shorten with -t, slow down with -S, or raise -q to $((CRF + 3))."
else
  echo "  ✓  ${MB} MB at 1920 — within budget."
fi
