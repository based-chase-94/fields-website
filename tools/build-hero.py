#!/usr/bin/env python3
"""
Fields — the hero headline.

    python3 tools/build-hero.py

Sets the headline in Heart of the Land outlines and writes it into
site/index.html between the headline markers.

Two sets of lines ship, and the stylesheet shows one:

  wide    two lines, broken after "Fields"
  narrow  three lines, for phones

The narrow set exists because the type size is set by the LONGEST line. On a
375px screen the two-line break caps the cap height at 23px; splitting into
three takes the longest line from 10.4em to 7.5em and the cap height to 32px.

The breaks follow the phrase rather than balancing widths. "A world of /
Fields in / your bowl" is more even and sets a little larger still, but
"Fields in" dangles.

The real words appear once, as hidden text on the heading itself; both drawn
sets are decorative. Emitting the text with each set would duplicate the
phrase for crawlers and read it twice to a screen reader.

The face is unicase, so casing here is immaterial. It is rendered to outlines
rather than served; see tools/scripttype.py.
"""

import pathlib
import re
import sys

try:
    import scripttype
except ImportError:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import scripttype

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "site/index.html"

START, END = "<!-- headline:start -->", "<!-- headline:end -->"

PHRASE = "A world of Fields in your bowl"
SETS = {
    "wide":   ["A world of Fields", "in your bowl"],
    "narrow": ["A world", "of Fields", "in your bowl"],
}
TRACKING = 0.015


def line_svg(text):
    return scripttype.render(text, font_path=scripttype.HEART,
                             css_class="hero__headline-line",
                             tracking=TRACKING, aria_hidden=True)


def ratio(text):
    return float(re.search(r"--sw:([\d.]+)", line_svg(text)).group(1))


def line_set(name, lines):
    """One set. --maxsw is the widest line's width in ems; the stylesheet
    divides the available width by it so every line in the set shares a
    font-size, and therefore a cap height."""
    widest = max(ratio(l) for l in lines)
    body = "\n".join(f'<span class="hero__line">{line_svg(l)}</span>' for l in lines)
    return (f'<span class="hero__lines hero__lines--{name}" '
            f'style="--maxsw:{widest:.4f}" aria-hidden="true">\n{body}\n</span>')


def build():
    return (f'<span class="vh">{PHRASE}</span>\n'
            + "\n".join(line_set(n, ls) for n, ls in SETS.items()))


def main():
    block = build()
    s = INDEX.read_text(encoding="utf-8")
    assert s.count(START) == 1 and s.count(END) == 1, "headline markers missing"
    out, n = re.subn(re.escape(START) + r".*?" + re.escape(END),
                     lambda _: START + "\n" + block + "\n" + END, s, flags=re.S)
    assert n == 1 and block in out, "headline substitution did not apply"
    INDEX.write_text(out, encoding="utf-8")
    print(f"headline: {len(block)/1024:.1f} KB")
    for name, lines in SETS.items():
        widest = max(ratio(l) for l in lines)
        print(f"  {name:7} {len(lines)} lines, widest {widest:5.2f}em  "
              f"({' / '.join(lines)})")


if __name__ == "__main__":
    main()
