# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Draw the README's generated art into assets/: trainer-sheet header, commit skyline, Pokémon card.

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
    rows = [
        ("YEARS", "5 in production ML and LLMs"),
        ("PROOF", "Nubank · fraud ML for a US bank"),
    ]
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="200" viewBox="0 0 640 200">',
        "<title>Vitor Pinheiro, AI/ML engineer: trainer sheet</title>",
        f"<style>text{{font-family:{SANS}}} .m{{font-family:{MONO}}}</style>",
        f'<rect x="1.5" y="1.5" width="637" height="197" rx="14" fill="{t["bg"]}" stroke="{t["edge"]}" stroke-width="3"/>',
        f'<rect x="22" y="26" width="148" height="148" rx="10" fill="{t["chip"]}" stroke="{t["accent"]}" stroke-width="3"/>',
        f'<image x="30" y="34" width="132" height="132" style="image-rendering:pixelated" href="data:image/png;base64,{AVATAR}"/>',
        f'<text class="m" x="196" y="40" font-size="14" letter-spacing="3" fill="{t["soft"]}">TRAINER SHEET</text>',
        f'<text x="196" y="76" font-size="32" font-weight="800" fill="{t["ink"]}">Vitor Pinheiro</text>',
        f'<text x="196" y="102" font-size="19" font-weight="700" fill="{t["accent"]}">AI/ML Engineer · Dark type</text>',
    ]
    for i, (k, v) in enumerate(rows):
        y = 132 + i * 26
        out.append(f'<text class="m" x="196" y="{y}" font-size="14" font-weight="700" fill="{t["soft"]}">{k}</text>')
        out.append(f'<text x="282" y="{y}" font-size="16" fill="{t["ink"]}">{esc(v)}</text>')
    out.append(f'<circle cx="203" cy="178" r="5" fill="{t["ok"]}"/>')
    out.append(f'<text x="216" y="184" font-size="16" font-weight="700" fill="{t["ok"]}">Open to remote roles</text>')
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


# ---------- Pokémon card -----------------------------------------------------------------------


def pokemon() -> str:
    W, H = 540, 135
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <title>Pokémon-style card: Vitor, basic Dark type, AI/ML engineer</title>
  <style>
    text {{ font-family: {SANS}; }}
    .m {{ font-family: {MONO}; }}
    .sheen {{ animation: sweep 6s ease-in-out infinite; }}
    @keyframes sweep {{ 0%, 100% {{ transform: translateX(-340px) skewX(-18deg); }} 50% {{ transform: translateX(340px) skewX(-18deg); }} }}
  </style>
  <defs>
    <linearGradient id="base" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#241b2e"/><stop offset="0.55" stop-color="#15121c"/><stop offset="1" stop-color="#1c1410"/>
    </linearGradient>
    <linearGradient id="holo" x1="0" y1="0" x2="1" y2="0.4">
      <stop offset="0" stop-color="#ff5f6d"/><stop offset="0.2" stop-color="{ORANGE}"/><stop offset="0.4" stop-color="#ffe66b"/>
      <stop offset="0.6" stop-color="#4ef0a8"/><stop offset="0.8" stop-color="{BLUE}"/><stop offset="1" stop-color="#b48cff"/>
    </linearGradient>
    <linearGradient id="beam" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
      <stop offset="0.5" stop-color="#fff" stop-opacity="0.22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
    <radialGradient id="art" cx="50%" cy="55%" r="65%"><stop offset="0" stop-color="#2d6f9a"/><stop offset="1" stop-color="#0f1722"/></radialGradient>
    <clipPath id="card"><rect x="3" y="3" width="{W - 6}" height="{H - 6}" rx="10"/></clipPath>
  </defs>
  <rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="12" fill="{GOLD}"/>
  <g clip-path="url(#card)">
    <rect width="{W}" height="{H}" fill="url(#base)"/>
    <rect width="{W}" height="{H}" fill="url(#holo)" opacity="0.16"/>
    <rect class="sheen" x="200" y="-10" width="120" height="{H + 20}" fill="url(#beam)"/>
  </g>
  <rect x="12" y="12" width="112" height="111" rx="6" fill="url(#art)" stroke="{GOLD}" stroke-width="2"/>
  <image x="18" y="17" width="100" height="100" style="image-rendering:pixelated" href="data:image/png;base64,{AVATAR}"/>
  <text class="m" x="138" y="26" font-size="11" letter-spacing="1.5" fill="#a89a82">BASIC · DARK TYPE</text>
  <text x="138" y="52" font-size="26" font-weight="800" fill="#f5e6c8">Vitor</text>
  <text x="{W - 16}" y="52" font-size="16" font-weight="800" fill="#ff6b6b" text-anchor="end">HP 5</text>
  <text x="138" y="88" font-size="15" font-weight="700" fill="{ORANGE}">Ship It</text>
  <text x="138" y="108" font-size="12" fill="#c9bba0">ML and LLM systems in production</text>
</svg>"""


def main() -> None:
    write("header-dark.svg", header("dark"))
    write("header-light.svg", header("light"))
    try:
        weeks = contributions()
        write("skyline-dark.svg", skyline("dark", weeks))
        write("skyline-light.svg", skyline("light", weeks))
    except Exception as e:  # noqa: BLE001 - keep the old art on any failure
        print("skyline kept:", e)
    try:
        write("pokemon-card.svg", pokemon())
    except Exception as e:  # noqa: BLE001
        print("card kept:", e)


if __name__ == "__main__":
    main()
