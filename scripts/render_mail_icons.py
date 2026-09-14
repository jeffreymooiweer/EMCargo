"""Render the small glyphs the HTML mail needs, as PNG.

Mail is not the browser. Gmail strips inline ``<svg>`` outright, so a glyph
that is one line of markup in the interface has to arrive as a raster image
attached to the message. This script is the bridge, and it exists as a script
rather than as a one-off so the asset can be regenerated when the drawing or
the colour changes — a binary in a repository nobody can rebuild is a fact
without a source.

**The drawing is the application's own.** ``docs/data-sources.md`` records that
the copy, delete, pencil and chevron glyphs are hand-written paths in the
shared icon module; this takes the copy glyph from
``frontend/src/components/icons.tsx`` verbatim, so the mail and the
interface show one drawing and there is no third-party licence to carry into
the mail.

**The colour is a compromise, deliberately.** Gmail's dark mode inverts the
card behind this icon but never the icon itself, so a glyph drawn in the text
colour disappears on exactly the phone the request came from. Slate 500 is the
template's own secondary colour and holds about 4:1 against the light card and
about 3:1 against Gmail's dark one — not beautiful on either, legible on both,
which for an icon that only has to be recognised is the right trade.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import fitz

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "backend" / "app" / "assets" / "copy.png"

#: The template's secondary text colour (slate 500).
STROKE = "#64748b"

#: Displayed at 18 px in the message; rendered at three times that so it stays
#: sharp on a phone, which is where a sign-in code is read.
DISPLAY_PX = 18
SCALE = 3

#: Verbatim from icons.tsx's CopyIcon, including the 24x24 viewBox
#: and the 1.7 stroke, so the two drawings cannot drift apart.
COPY_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'width="24" height="24" fill="none" stroke="{stroke}" stroke-width="1.7" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M9 9h12v12H9z M15 9V3H3v12h6" />'
    "</svg>"
)


def render(destination: Path = OUT) -> Path:
    svg = COPY_SVG.format(stroke=STROKE)
    with fitz.open(stream=svg.encode("utf-8"), filetype="svg") as document:
        page = document[0]
        zoom = (DISPLAY_PX * SCALE) / page.rect.width
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(destination)
    return destination


def render_logo() -> Path:
    """Render the website's SVG filter, which MuPDF does not implement."""
    destination = OUT.with_name("logo.png")
    subprocess.run(
        ["node", str(REPO / "frontend" / "scripts" / "render-brand.mjs"), str(destination)],
        check=True,
    )
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--logo", action="store_true", help="Also regenerate the mail logo from emcargo.svg")
    args = parser.parse_args()
    written = render(args.out)
    print(f"{written} ({written.stat().st_size} bytes)")
    if args.logo:
        print(render_logo())
