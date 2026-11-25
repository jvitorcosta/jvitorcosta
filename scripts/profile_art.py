# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Draw the README's generated art into assets/: trainer-sheet header and commit skyline.

Run with: uv run scripts/profile_art.py
Env: GH_USER (default jvitorcosta), GITHUB_TOKEN (unused now; kept for the API rate limit if needed).

Everything is plain SVG with the avatar embedded as base64, because GitHub does not load external
images inside an SVG. If a data source can't be read, the existing file is kept and the script
still exits 0 (the daily refresh must not fail on a flaky network).
"""

import base64
import html
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
AVATAR = base64.b64encode((ASSETS / "avatar.png").read_bytes()).decode()
SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

# Palette: the site's warm cream and ink, the orange of the old snake, the blue of the avatar's flames.
ORANGE, BLUE, GOLD, GREEN = "#f0802c", "#40bcf4", "#e8b04a", "#00e054"


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
    "dark": dict(bg="#14110f", edge="#3a2a1c", ink="#f5e6c8", soft="#a89a82", accent=ORANGE, chip="#201a16", ok=GREEN),
    "light": dict(bg="#f5e6c8", edge="#8a5a12", ink="#3a1410", soft="#6b4a3a", accent="#a3161a", chip="#ead2a8", ok="#0a7a35"),
}


def header(mode: str) -> str:
    t = THEMES[mode]
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="170" viewBox="0 0 640 170">',
        "<title>Vitor Pinheiro, AI/ML engineer: trainer sheet</title>",
        f"<style>text{{font-family:{SANS}}} .m{{font-family:{MONO}}}</style>",
        f'<rect x="1.5" y="1.5" width="637" height="167" rx="14" fill="{t["bg"]}" stroke="{t["edge"]}" stroke-width="3"/>',
        f'<rect x="22" y="20" width="130" height="130" rx="10" fill="{t["chip"]}" stroke="{t["accent"]}" stroke-width="3"/>',
        f'<image x="28" y="26" width="118" height="118" style="image-rendering:pixelated" href="data:image/png;base64,{AVATAR}"/>',
        f'<text class="m" x="178" y="40" font-size="14" letter-spacing="3" fill="{t["soft"]}">TRAINER SHEET</text>',
        f'<text x="178" y="78" font-size="32" font-weight="800" fill="{t["ink"]}">Vitor Pinheiro</text>',
        f'<text x="178" y="104" font-size="19" font-weight="700" fill="{t["accent"]}">AI/ML Engineer · Dark type</text>',
    ]
    out.append(f'<circle cx="185" cy="132" r="5" fill="{t["ok"]}"/>')
    out.append(f'<text x="198" y="138" font-size="16" font-weight="700" fill="{t["ok"]}">Open to remote roles</text>')
    out.append("</svg>")
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


def skyline(mode: str, weeks: list[list[int]]) -> str:
    dark = mode == "dark"
    bg, ground = ("#0d0b14", "#2a2140") if dark else ("#f5e6c8", "#8a5a12")
    far = "#17122a" if dark else "#e3cfa6"
    body = "#120f1c" if dark else "#fff7e6"
    dim = "#2b2540" if dark else "#d9c39a"
    txt = "#a89ec8" if dark else "#6b4a3a"
    W, H, base = 840, 200, 164
    n = len(weeks)
    slot = (W - 40) / n
    bw = slot * 0.74
    totals = [sum(w) for w in weeks]
    peak = max(max(totals), 1)
    total = sum(totals)
    active = sum(1 for w in weeks for d in w if d)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f"<title>Commit skyline: {total} contributions in the last year</title>",
        "<defs>",
        '<filter id="glow" x="-60%" y="-30%" width="220%" height="160%"><feGaussianBlur stdDeviation="2.6" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        f'<linearGradient id="neon" x1="0" x2="1"><stop offset="0" stop-color="{BLUE}"/><stop offset="1" stop-color="{ORANGE}"/></linearGradient>',
        "</defs>",
        f'<rect width="{W}" height="{H}" rx="14" fill="{bg}"/>',
    ]
    # Far skyline: a fixed, deterministic silhouette for depth.
    x = 20.0
    i = 0
    while x < W - 30:
        w = 16 + (i * 7) % 14
        h = 22 + (i * 37) % 46
        out.append(f'<rect x="{x:.1f}" y="{base - h}" width="{w}" height="{h}" fill="{far}"/>')
        x += w + 2
        i += 1
    for k, week in enumerate(weeks):
        t = totals[k]
        h = 5 + 118 * math.sqrt(t / peak) if t else 5
        x0 = 20 + k * slot + (slot - bw) / 2
        frac = k / max(n - 1, 1)
        stroke = "url(#neon)" if t else dim
        glow = ' filter="url(#glow)"' if t else ""
        out.append(f'<rect x="{x0:.1f}" y="{base - h:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{body}"/>')
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
    out.append(f'<rect x="20" y="{base}" width="{W - 40}" height="2" fill="{ground}"/>')
    out.append(
        f'<text x="20" y="190" font-family="{MONO}" font-size="14" fill="{txt}">'
        f"{total} contributions · {active} active days · last 12 months</text>"
    )
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    write("header-dark.svg", header("dark"))
    write("header-light.svg", header("light"))
    try:
        weeks = contributions()
        write("skyline-dark.svg", skyline("dark", weeks))
        write("skyline-light.svg", skyline("light", weeks))
    except Exception as e:  # noqa: BLE001 - keep the old art on any failure
        print("skyline kept:", e)


if __name__ == "__main__":
    main()
