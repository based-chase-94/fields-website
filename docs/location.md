# The location section

`tools/build-location.py` writes two things into `site/index.html`: the
heading, and the map.

```bash
python3 tools/build-location.py
python3 tools/stamp-assets.py   # only if CSS or JS also changed
```

## The heading

"See you in the fields." is set in **Heart of the Land** and rendered to SVG
outlines, the same treatment Midstar gets on the menu titles, and for a
blunter reason: nobody has the purchase record, so nobody knows whether a web
licence was ever bought.

Unlike Midstar, the file carries no embedded prohibition — no licence
description, no licence URL. That is not a grant. `fsType` is 8 (Editable
Embedding), which governs embedding in *documents*, not serving a webfont, so
it does not speak to this either way. If the EULA turns up and covers web use,
it is an 11 KB woff2 and the swap is small.

The face is **unicase**: all 26 lowercase glyphs are byte-identical to their
capitals, verified by comparing outlines rather than advance widths. Source
casing is therefore immaterial — it sets as caps regardless. That is also why
it suits this heading and would ruin the menu titles, where Midstar's script
is doing the work.

## The map

## Why drawn

A raster tile service bakes every building name, bus stop and parking icon
into the image — there is no way to take them out afterwards, and the brief
was street names only. Three other things settled it:

- CARTO's light basemap now needs an API key. Its tiles still return **200**,
  carrying "API KEY REQUIRED" as artwork. A screenshot would have shipped that
  without complaint; it was caught only by looking at the picture.
- Drawing it puts the map in the brand palette by construction rather than
  filtering someone else's palette toward it.
- The result is ~15 KB gzipped and sharp at any size. No screenshot is both.

## Refreshing the data

`source/map/` holds three Overpass responses so builds need no network. To
refresh, re-run these against `https://overpass-api.de/api/interpreter` (the
public endpoint returns 502 when busy; `overpass.private.coffee` is a mirror):

```
[out:json][timeout:60];
( way["highway"](39.743264,-104.842990,39.746964,-104.838320); );
out geom;
```

Swap the filter for `way["building"]` → `bldg.json`, and
`way["leisure"~"^(park|garden|pitch|playground)$"]` plus the `landuse` and
`natural` equivalents → `green.json`.

## What is where

`HOME_ID` is the OSM way for the building named **Research 2**. The build
asserts it is present, so a data refresh that drops or renumbers it fails
loudly instead of quietly rendering a map with nothing marked.

The pin sits at the geocode of 12700 E 19th Ave, which falls **inside** that
footprint, 9 m from its centroid — independent confirmation that the address
and the building agree.

The building is outlined, never filled: a fill swallows the marker inside it.
9px against 1.5px on every other building.

## Labels

Street names only. No building names, no POIs, no icons.

A label is centred on its road, so testing the anchor point against the frame
is not enough — a long name overruns a point that is itself well inside, and
`slice` then crops it. The extent is projected along the segment direction
instead: reserving half the text on *both* axes is the obvious guard and it
throws away every long name.

## Attribution

OpenStreetMap data is ODbL. The credit beside the map is a licence condition,
not decoration. Leave it in, and keep it legible — it measures 5.6:1.
