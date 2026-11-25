# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow"]
# ///
"""One-off: turn the pixel-art portrait into coloured ASCII for the header.

Run with: uv run scripts/make_ascii_portrait.py <portrait image>
Writes assets/portrait-dark.json and portrait-light.json: rows of [text, colour] runs. The source image
is not kept in the repo; the daily Action only reads these files.
Glyph density follows brightness (dark theme) or darkness (light theme); the colour follows the pixel,
pulled into a range that stays readable on the card.
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageEnhance

COLS = 54
RAMP = " .,:;i1tfLCG08@"
OUT = Path(__file__).resolve().parent.parent / "assets"


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def hexc(c: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % c


def main(src: str) -> None:
    img = Image.open(src).convert("RGB")
    w, h = img.size
    img = img.crop((int(w * 0.34), int(h * 0.30), int(w * 0.82), int(h * 0.63)))  # helmet rim, glasses, ear, scarf
    img = ImageEnhance.Contrast(img).enhance(1.35)
    bg = img.getpixel((3, 3))
    cw, ch = img.size
    rows = round(COLS * ch / cw * 0.5)  # a glyph is about twice as tall as wide
    small = img.resize((COLS, rows), Image.BOX)
    for theme in ("dark", "light"):
        out = []
        for y in range(rows):
            runs: list[list[str]] = []
            for x in range(COLS):
                px = small.getpixel((x, y))
                if sum(abs(a - c) for a, c in zip(px, bg)) < 100:  # the purple backdrop
                    ch_, col = " ", "#000000"
                else:
                    lum = (0.299 * px[0] + 0.587 * px[1] + 0.114 * px[2]) / 255
                    if theme == "dark":
                        idx = max(2, round(lum ** 0.7 * (len(RAMP) - 1)))
                        col = hexc(mix((120, 96, 190), px, 0.55 + 0.45 * lum) if lum < 0.35 else mix(px, (255, 255, 255), 0.1))
                    else:
                        idx = max(2, round((1 - lum) ** 0.7 * (len(RAMP) - 1)))
                        col = hexc(mix(px, (40, 12, 70), 0.55) if lum > 0.35 else mix(px, (30, 8, 60), 0.35))
                    ch_ = RAMP[idx]
                if runs and runs[-1][1] == col:
                    runs[-1][0] += ch_
                else:
                    runs.append([ch_, col])
            out.append(runs)
        (OUT / f"portrait-{theme}.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"{COLS}x{rows}")


if __name__ == "__main__":
    main(sys.argv[1])
