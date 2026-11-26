# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Draw the README's generated art into assets/: the header and the commit skyline.

Run with: uv run scripts/profile_art.py
Env: GH_USER (default jvitorcosta), GITHUB_TOKEN (unused now; kept for the API rate limit if needed).

Everything is plain SVG (the portrait is ASCII text, see make_ascii_portrait.py), because GitHub does
not load external images inside an SVG. If a data source can't be read, the existing file is kept and the script
still exits 0 (the daily refresh must not fail on a flaky network).
"""

import html
import json
import math
import os
import re
import urllib.request
from urllib.parse import urlparse
from datetime import date
from pathlib import Path

USER = os.environ.get("GH_USER", "jvitorcosta")
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
UA = "Mozilla/5.0 (profile art; +https://github.com/jvitorcosta/jvitorcosta)"
SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

# Palette: purple, from the site's Nu purple (#820ad1), with violet and cyan neon.
ORANGE, BLUE, GOLD, GREEN = "#d28bff", "#40bcf4", "#e8b04a", "#00e054"  # ORANGE is now the violet neon


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    if (token := os.environ.get("GITHUB_TOKEN")) and urlparse(url).hostname == "api.github.com":
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https URLs
        return resp.read()


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def write(name: str, svg: str) -> None:
    (ASSETS / name).write_text(svg, encoding="utf-8")
    print("wrote", name)


# ---------- header ----------------------------------------------------------------------------

THEMES = {
    "dark": dict(bg="#150d24", edge="#3b2466", ink="#efe6ff", soft="#a99bc9", accent="#b57cff", chip="#20123a", ok=GREEN),
    "light": dict(bg="#f1e8ff", edge="#820ad1", ink="#2a0845", soft="#6b4a8f", accent="#820ad1", chip="#e2d2fa", ok="#0a7a35"),
}


def portrait(mode: str, ink: str) -> str:
    """The coloured ASCII portrait: one <tspan> per row (textLength keeps the width the same on every font),
    with nested tspans for runs of one colour."""
    rows = json.loads((ASSETS / f"portrait-{mode}.json").read_text(encoding="utf-8"))
    cols = max(sum(len(t) for t, _ in runs) for runs in rows)
    width, step = 146, 6.0
    out = []
    for i, runs in enumerate(rows):
        line = "".join(f'<tspan fill="{c}">{esc(t)}</tspan>' for t, c in runs)
        n = sum(len(t) for t, _ in runs)
        out.append(f'<tspan x="27" y="{28 + i * step:.1f}" textLength="{width * n / cols:.1f}" lengthAdjust="spacing">{line}</tspan>')
    return f'<text class="m" font-size="6.0" fill="{ink}" xml:space="preserve" aria-hidden="true">{"".join(out)}</text>'


def header(mode: str) -> str:
    """840x220, drawn large so the name still reads when a phone scales it to about 40%."""
    t = THEMES[mode]
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="840" height="220" viewBox="0 0 840 220">',
        "<title>Vitor Pinheiro, AI/ML Software Engineer</title>",
        f"<style>text{{font-family:{SANS}}} .m{{font-family:{MONO}}}</style>",
        f'<rect x="2" y="2" width="836" height="216" rx="20" fill="{t["bg"]}" stroke="{t["edge"]}" stroke-width="4"/>',
        # The portrait is laid out in a 168x168 box at (18, 16); scale that box to 180x180 at (20, 20).
        f'<g transform="translate(20 20) scale({180 / 168:.4f}) translate(-18 -16)">',
        f'<rect x="18" y="16" width="168" height="168" rx="10" fill="{t["chip"]}" stroke="{t["accent"]}" stroke-width="2.5"/>',
        portrait(mode, t["ink"]),
        "</g>",
        f'<text x="236" y="108" font-size="60" font-weight="800" fill="{t["ink"]}">Vitor Pinheiro</text>',
        f'<text x="236" y="160" font-size="34" font-weight="700" fill="{t["accent"]}">AI/ML Software Engineer</text>',
        "</svg>",
    ]
    return "\n".join(out)


def header_phone(mode: str) -> str:
    """600x450, portrait above the name, so the header is not a thin strip on a phone."""
    t = THEMES[mode]
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="450" viewBox="0 0 600 450">',
        "<title>Vitor Pinheiro, AI/ML Software Engineer</title>",
        f"<style>text{{font-family:{SANS}}} .m{{font-family:{MONO}}}</style>",
        f'<rect x="2" y="2" width="596" height="446" rx="24" fill="{t["bg"]}" stroke="{t["edge"]}" stroke-width="4"/>',
        f'<g transform="translate(175 30) scale({250 / 168:.4f}) translate(-18 -16)">',
        f'<rect x="18" y="16" width="168" height="168" rx="10" fill="{t["chip"]}" stroke="{t["accent"]}" stroke-width="2"/>',
        portrait(mode, t["ink"]),
        "</g>",
        f'<text x="300" y="358" text-anchor="middle" font-size="62" font-weight="800" fill="{t["ink"]}">Vitor Pinheiro</text>',
        f'<text x="300" y="410" text-anchor="middle" font-size="36" font-weight="700" fill="{t["accent"]}">AI/ML Software Engineer</text>',
        "</svg>",
    ]
    return "\n".join(out)


# ---------- commit skyline --------------------------------------------------------------------


def contributions() -> list[list[int]]:
    """Weeks of 7 daily counts (Sunday first), from the public contribution graph."""
    page = get(f"https://github.com/users/{USER}/contributions").decode()
    cells = re.findall(r'data-date="([\d-]+)" id="(contribution-day-component-\d+-\d+)" data-level="(\d)"', page)
    tips = dict(re.findall(r'for="(contribution-day-component-\d+-\d+)"[^>]*>\s*([^<]*?)\s*<', page))
    days = {}
    for d, cid, _level in cells:
        m = re.match(r"(\d+) contribution", tips.get(cid, ""))
        days[d] = int(m.group(1)) if m else 0
    ordered = sorted(days)
    if not ordered:
        raise ValueError("no contribution cells found")
    first = date.fromisoformat(ordered[0])
    pad = (first.weekday() + 1) % 7  # weekday() Monday=0; the graph starts on Sunday
    flat = [0] * pad + [days[d] for d in ordered]
    flat += [0] * (-len(flat) % 7)
    return [flat[i : i + 7] for i in range(0, len(flat), 7)]


def colours(mode: str) -> dict:
    dark = mode == "dark"
    return dict(
        bg="#150d24" if dark else "#f1e8ff",
        ground="#3b2466" if dark else "#820ad1",
        far="#1d1233" if dark else "#e0d0f7",
        body="#0f0919" if dark else "#fbf7ff",
        dim="#33214f" if dark else "#d3c0f0",
        txt="#a99bc9" if dark else "#6b4a8f",
    )


def svg_open(mode: str, weeks: list[list[int]], width: int, height: int) -> list[str]:
    total = sum(sum(w) for w in weeks)
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f"<title>Commit skyline: {total} contributions in the last year</title>",
        "<defs>",
        '<filter id="glow" x="-60%" y="-30%" width="220%" height="160%"><feGaussianBlur stdDeviation="2.6" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        # In user space, so one gradient spans the chart and a flat cap still gets a colour.
        f'<linearGradient id="neon" gradientUnits="userSpaceOnUse" x1="0" x2="{width}">'
        f'<stop offset="0" stop-color="{BLUE}"/><stop offset="1" stop-color="{ORANGE}"/></linearGradient>',
        "</defs>",
        f'<rect width="{width}" height="{height}" rx="14" fill="{colours(mode)["bg"]}"/>',
    ]


def street(mode: str, weeks: list[list[int]], peak: int, width: int, base: int, offset: int, count: int) -> list[str]:
    """One row of buildings on its ground line: weeks[i] is week offset + i of count."""
    c = colours(mode)
    slot = (width - 40) / len(weeks)
    bw = slot * 0.74
    out = []
    # Far skyline: a fixed, deterministic silhouette for depth.
    x = 20.0
    i = offset
    while x < width - 30:
        w = 16 + (i * 7) % 14
        w = min(w, width - 20 - x)
        h = 22 + (i * 37) % 46
        out.append(f'<rect x="{x:.1f}" y="{base - h}" width="{w:.0f}" height="{h}" fill="{c["far"]}"/>')
        x += w + 2
        i += 1
    for k, week in enumerate(weeks):
        t = sum(week)
        h = 5 + 118 * math.sqrt(t / peak) if t else 5
        x0 = 20 + k * slot + (slot - bw) / 2
        frac = (offset + k) / max(count - 1, 1)
        stroke = "url(#neon)" if t else c["dim"]
        glow = ' filter="url(#glow)"' if t else ""
        out.append(f'<rect x="{x0:.1f}" y="{base - h:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{c["body"]}"/>')
        out.append(f'<rect x="{x0:.1f}" y="{base - h:.1f}" width="{bw:.1f}" height="3" fill="{stroke}"{glow}/>')
        # One lit window per active day, stacked from the ground, brighter for busier days.
        lit = [d for d in week if d]
        for j, d in enumerate(lit):
            wy = base - 7 - j * 8
            if wy < base - h + 6:
                break
            op = 0.45 + 0.55 * min(d / 6, 1)
            col = ORANGE if frac > 0.5 else BLUE
            out.append(
                f'<rect x="{x0 + bw * 0.22:.1f}" y="{wy}" width="{bw * 0.56:.1f}" height="4" fill="{col}" opacity="{op:.2f}"/>'
            )
    out.append(f'<rect x="20" y="{base}" width="{width - 40}" height="2" fill="{c["ground"]}"/>')
    return out


def totals(weeks: list[list[int]]) -> tuple[int, int]:
    return sum(sum(w) for w in weeks), sum(1 for w in weeks for d in w if d)


def skyline(mode: str, weeks: list[list[int]]) -> str:
    peak = max(max(sum(w) for w in weeks), 1)
    total, active = totals(weeks)
    out = svg_open(mode, weeks, 840, 200)
    out += street(mode, weeks, peak, 840, 164, 0, len(weeks))
    out.append(
        f'<text x="20" y="190" font-family="{MONO}" font-size="14" fill="{colours(mode)["txt"]}">'
        f"{total} contributions · {active} active days · last 12 months</text>"
    )
    out.append("</svg>")
    return "\n".join(out)


def skyline_phone(mode: str, weeks: list[list[int]]) -> str:
    """The same year in two rows of half the weeks, so buildings and caption stay readable on a phone."""
    peak = max(max(sum(w) for w in weeks), 1)
    total, active = totals(weeks)
    half = len(weeks) // 2
    out = svg_open(mode, weeks, 420, 350)
    out += street(mode, weeks[:half], peak, 420, 140, 0, len(weeks))
    out += street(mode, weeks[half:], peak, 420, 280, half, len(weeks))
    txt = colours(mode)["txt"]
    for y, line in ((310, f"{total} contributions"), (334, f"{active} active days · last 12 months")):
        out.append(f'<text x="20" y="{y}" font-family="{MONO}" font-size="18" fill="{txt}">{line}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    write("header-dark.svg", header("dark"))
    write("header-light.svg", header("light"))
    write("header-phone-dark.svg", header_phone("dark"))
    write("header-phone-light.svg", header_phone("light"))
    try:
        weeks = contributions()
        write("skyline-dark.svg", skyline("dark", weeks))
        write("skyline-light.svg", skyline("light", weeks))
        write("skyline-phone-dark.svg", skyline_phone("dark", weeks))
        write("skyline-phone-light.svg", skyline_phone("light", weeks))
    except Exception as e:  # noqa: BLE001 - keep the old art on any failure
        print("skyline kept:", e)


if __name__ == "__main__":
    main()
