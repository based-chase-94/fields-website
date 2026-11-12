#!/usr/bin/env bash
# Fields — the moving grass behind the in-store menu board pages (site/screens/).
#
#   bash tools/encode-screen-loops.sh            # every board, 1080p and 4K
#   bash tools/encode-screen-loops.sh house-bowls
#
# Reads source/video/grass.mp4 (the coming-soon footage, 3840x2160, 29.97 fps,
# 584 frames; gitignored, 185 MB) and writes text-free loops to
# source/video/screens/<board>-<1080|2160>.mp4. tools/build-screens.py then
# copies them into the site under a content-hashed name.
#
# This is the same treatment as the baked TV masters in fields-digital-menu
# (tools/grass-look.mjs), so the pages and the old videos match:
#   - brightness 0.85 (the client's pick, 21 Oct 2026), Gaussian blur sigma 3
#     at 3840 px wide (scaled with the output width);
#   - frames relabelled as 30 fps (0.1% faster than 29.97, so no frame is
#     dropped or doubled), cut by frame number;
#   - the last 30 frames crossfaded into the first, and xfade's one extra frame
#     trimmed, so the loop point is seamless.
# Each board starts at its own moment in the footage, like the Stills did, so
# each board gets its own file, rotated to start there. No seeking in the page.
#
# No text is burned in, so the bitrate goes on grass alone: blurred grass
# compresses well. Cloudflare Workers static assets cap a file at 25 MiB.
set -euo pipefail
cd "$(dirname "$0")/.."

SRC=source/video/grass.mp4
OUT=source/video/screens
TOTAL=584     # frames in the footage
FADE=30       # crossfade frames
FRAMES=$((TOTAL - FADE))
mkdir -p "$OUT"

# board -> start time in seconds (grass-look.mjs START)
declare -A START=([house-bowls]=0 [grow-your-own]=9.5 [proteins-upgrades]=17.5)
BOARDS=("${@:-house-bowls grow-your-own proteins-upgrades}")
# shellcheck disable=SC2206
BOARDS=(${BOARDS[*]})

encode() {  # board width height crf preset level [maxrate]
  local board=$1 w=$2 h=$3 crf=$4 preset=$5 level=$6 cap=${7:-}
  local sigma off start out
  sigma=$(python3 -c "print(3 * $w / 3840)")
  off=$(python3 -c "print(($FRAMES - $FADE) / 30)")
  start=$(python3 -c "print(round(${START[$board]} * 30) % $FRAMES)")
  out="$OUT/$board-$h.mp4"
  local look="scale=$w:$h:flags=lanczos,gblur=sigma=$sigma,colorchannelmixer=rr=0.85:gg=0.85:bb=0.85"
  local graph="[0:v]setpts=N/30/TB,$look,split[a][b];"
  graph+="[a]trim=start_frame=$FADE,setpts=PTS-STARTPTS[body];"
  graph+="[b]trim=end_frame=$FADE,setpts=PTS-STARTPTS[head];"
  graph+="[body][head]xfade=transition=fade:duration=$((FADE / 30)):offset=$off,trim=end_frame=$FRAMES,split[l1][l2];"
  # Rotate the loop so it starts at the board's moment: frames [start, end) then [0, start).
  graph+="[l1]trim=start_frame=$start,setpts=PTS-STARTPTS[tail];"
  graph+="[l2]trim=end_frame=$start,setpts=PTS-STARTPTS[lead];"
  if [ "$start" -eq 0 ]; then
    graph+="[tail]format=yuv420p[v];[lead]nullsink"
  else
    graph+="[tail][lead]concat=n=2:v=1,format=yuv420p[v]"
  fi
  ffmpeg -y -loglevel error -i "$SRC" -filter_complex "$graph" -map '[v]' -an -r 30 -frames:v "$FRAMES" \
    -c:v libx264 -profile:v high -level:v "$level" -preset "$preset" -crf "$crf" ${cap:+-maxrate $cap -bufsize $((${cap%M} * 2))M} -movflags +faststart "$out"
  printf '  %s  %s MB\n' "$out" "$(python3 -c "import os; print(round(os.path.getsize('$out') / 1e6, 1))")"
}

for b in "${BOARDS[@]}"; do
  [ -n "${START[$b]+x}" ] || { echo "unknown board: $b" >&2; exit 1; }
  encode "$b" 1920 1080 30 slow 4.2
  # 4K at CRF 30 alone is ~46 MB; a 9 Mbps cap keeps it near 21 MB, under the 25 MiB limit.
  encode "$b" 3840 2160 30 medium 5.1 9M
done
