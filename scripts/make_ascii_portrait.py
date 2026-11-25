# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow"]
# ///
"""One-off: turn the pixel-art portrait into ASCII for the header (assets/portrait-dark.txt, portrait-light.txt).

Run with: uv run scripts/make_ascii_portrait.py <portrait image>
The source image is not kept in the repo; the two text files are what the header script reads.
Dark theme: brighter pixel, denser glyph (light ink on a dark card). Light theme: the reverse.
"""

import sys
from pathlib import Path

from PIL import Image

COLS = 56
RAMP = " .:-=+*#%@"
OUT = Path(__file__).resolve().parent.parent / "assets"


def main(src: str) -> None:
    img = Image.open(src).convert("RGB")
    w, h = img.size
    img = img.crop((int(w * 0.33), int(h * 0.20), int(w * 0.90), int(h * 0.66)))  # helmet, face and scarf
    bg = img.getpixel((4, 4))
    cw, ch = img.size
    rows = round(COLS * ch / cw * 0.5)  # a glyph is about twice as tall as wide
    small = img.resize((COLS, rows), Image.BOX)
    dark_lines, light_lines = [], []
    for y in range(rows):
        d, l = "", ""
        for x in range(COLS):
            r, g, b = small.getpixel((x, y))
            if sum(abs(a - c) for a, c in zip((r, g, b), bg)) < 90:  # the purple backdrop
                d += " "
                l += " "
                continue
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            d += RAMP[max(1, round(lum ** 0.8 * (len(RAMP) - 1)))]
            l += RAMP[max(1, round((1 - lum) ** 0.8 * (len(RAMP) - 1)))]
        dark_lines.append(d.rstrip())
        light_lines.append(l.rstrip())
    (OUT / "portrait-dark.txt").write_text("\n".join(dark_lines) + "\n", encoding="utf-8")
    (OUT / "portrait-light.txt").write_text("\n".join(light_lines) + "\n", encoding="utf-8")
    print(f"{COLS}x{rows}")


if __name__ == "__main__":
    main(sys.argv[1])
