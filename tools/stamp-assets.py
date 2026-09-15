#!/usr/bin/env python3
"""
Fields — cache-bust the stylesheet and script.

    python3 tools/stamp-assets.py

GitHub Pages serves assets with a ten-minute max-age, so a client reloading the
review link during a round of changes can sit on a stale site.css and see a
half-updated page. Stamping each reference with a hash of its own contents
means a changed file is always a new URL, and an unchanged one stays cached.

Run it after any edit to site/assets/css or site/assets/js. Safe to re-run —
it replaces an existing stamp rather than stacking another one on.
"""

import hashlib
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "site/index.html"
STAMPED = ["assets/css/site.css", "assets/js/site.js"]


def main():
    html = INDEX.read_text()
    for rel in STAMPED:
        path = ROOT / "site" / rel
        if not path.exists():
            raise SystemExit(f"missing {rel}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:8]
        # Match the reference with or without an existing ?v=
        pattern = re.escape(rel) + r"(\?v=[0-9a-f]+)?"
        html, n = re.subn(pattern, f"{rel}?v={digest}", html)
        if not n:
            raise SystemExit(f"{rel} is not referenced in index.html")
        print(f"  {rel}  ->  ?v={digest}")
    INDEX.write_text(html)


if __name__ == "__main__":
    main()
