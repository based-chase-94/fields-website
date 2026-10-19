# The location map

Drawn, not screenshotted. `tools/build-map.py` renders OpenStreetMap data from
`source/map/` into `site/index.html` between the map markers.

```bash
python3 tools/build-map.py
python3 tools/stamp-assets.py   # only if CSS or JS also changed
```

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
