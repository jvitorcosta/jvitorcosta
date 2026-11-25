# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Draw assets/goodreads.svg and assets/strava.svg, the same 540x135 frame as the Spotify and Letterboxd cards.

- Goodreads: the book I'm reading, from my public Goodreads profile page.
- Strava: my latest activity, read from the row my own site already shows (no Strava token needed here;
  the site only publishes title, distance, time, speed and date: no map, route or heart rate).

Run with: uv run scripts/life_cards.py
If a source can't be read, the existing card is kept and the script still exits 0.
"""

import base64
import html
import re
import urllib.request
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
UA = "Mozilla/5.0 (profile card; +https://github.com/jvitorcosta/jvitorcosta)"
GOODREADS = "https://www.goodreads.com"
PROFILE = f"{GOODREADS}/user/show/185113793-vitor-pinheiro"
SITE = "https://jvitorcosta.github.io/"
W, H, PAD = 540, 135, 7
BG = "#150d24"
SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
TAN, CREAM, STRAVA = "#b79cf0", "#f1e9ff", "#fc4c02"

# The 20x20 pixel Strava tile from my site, drawn as rects.
STRAVA_TILE = (
    '<rect width="20" height="20" fill="#fc4c02"/>'
    + "".join(
        f'<rect x="{x}" y="{y}" width="{w}" height="1" fill="#fff"/>'
        for x, y, w in [
            (8, 3, 2), (8, 4, 2), (7, 5, 4), (7, 6, 4), (6, 7, 6), (6, 8, 6), (5, 9, 3), (10, 9, 3),
            (5, 10, 2), (11, 10, 2), (4, 11, 3), (11, 11, 3), (8, 12, 2), (12, 12, 2), (9, 13, 2),
            (12, 13, 2), (9, 14, 4), (10, 15, 2), (10, 16, 2),
        ]
    )
)


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https URLs
        return resp.read()


def text(raw: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())


def clip(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def frame(title: str, body: str, extra_defs: str = "") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <title>{html.escape(title)}</title>
  <style>
    text {{ font-family: {SANS}; }}
    .label {{ font-size: 12px; font-weight: 600; letter-spacing: 1.5px; fill: #9a9a9a; }}
    .title {{ font-size: 24px; font-weight: 700; fill: {CREAM}; }}
    .meta {{ font-size: 15px; fill: #a8a8a8; }}
  </style>
  <defs>{extra_defs}</defs>
  <rect width="{W}" height="{H}" rx="5" fill="{BG}"/>
{body}
</svg>
"""


# ---------- Goodreads ----------------------------------------------------------------------------


def book() -> dict:
    page = get(PROFILE).decode("utf-8", errors="replace")
    start = page.find('id="currentlyReadingReviews"')
    if start < 0:
        raise ValueError("no currently-reading block")
    block = page[start:]
    first = block.find('class="Updates')
    entry = block[first + 1 :]
    second = entry.find('class="Updates')
    entry = block[first:] if second < 0 else entry[:second]
    title = re.search(r'<a[^>]*class="bookTitle"[^>]*>(.*?)</a>', entry, re.S)
    author = re.search(r'<a[^>]*class="authorName"[^>]*>(.*?)</a>', entry, re.S)
    cover = re.search(r'class="firstcol".*?<img[^>]*\ssrc="([^"]+)"', entry, re.S)
    progress = re.search(r"\(page (\d+) of (\d+)\)", entry)
    if not title:
        raise ValueError("no book title")
    return {
        "title": text(title.group(1)).split(":")[0].split(" (")[0],
        "author": text(author.group(1)) if author else "",
        "cover": html.unescape(cover.group(1)) if cover else "",
        "page": int(progress.group(1)) if progress else None,
        "pages": int(progress.group(2)) if progress else None,
    }


def goodreads_card(b: dict) -> str:
    ph = H - 2 * PAD
    pw = round(ph * 2 / 3)
    x = PAD + pw + 16
    try:
        img = base64.b64encode(get(b["cover"])).decode()
        poster = (
            f'<image x="{PAD}" y="{PAD}" width="{pw}" height="{ph}" clip-path="url(#poster)" '
            f'preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{img}"/>'
        )
    except Exception:  # noqa: BLE001 - the card is fine without a cover
        poster = f'<rect x="{PAD}" y="{PAD}" width="{pw}" height="{ph}" rx="4" fill="#3b2466"/>'
    bar = ""
    if b["page"] and b["pages"]:
        frac = min(b["page"] / b["pages"], 1)
        bw = W - x - 20
        bar = (
            f'<rect x="{x}" y="100" width="{bw}" height="8" rx="4" fill="#2c1b4d"/>'
            f'<rect x="{x}" y="100" width="{bw * frac:.0f}" height="8" rx="4" fill="{TAN}"/>'
            f'<text x="{x}" y="125" class="meta">page {b["page"]} of {b["pages"]} · {round(frac * 100)}%</text>'
        )
    body = f"""  {poster}
  <circle cx="{x + 5}" cy="23" r="5" fill="{TAN}"/>
  <text x="{x + 18}" y="27" class="label">CURRENTLY READING</text>
  <text x="{x}" y="58" class="title">{html.escape(clip(b["title"], 24))}</text>
  <text x="{x}" y="82" class="meta">{html.escape(clip(b["author"], 36))}</text>
{bar}"""
    return frame(
        f"Currently reading on Goodreads: {b['title']}",
        body,
        f'<clipPath id="poster"><rect x="{PAD}" y="{PAD}" width="{pw}" height="{ph}" rx="4"/></clipPath>',
    )


# ---------- Strava -------------------------------------------------------------------------------


def activity() -> dict:
    page = get(SITE).decode("utf-8", errors="replace")
    m = re.search(
        r'<div class="stv"[^>]*>.*?<span class="t">(.*?)</span>(.*?)<span lang="en">([^<]*)</span>'
        r'.*?class="strava-link" href="([^"]+)"',
        page,
        re.S,
    )
    if not m:
        raise ValueError("no Strava row on the site")
    name, rest, date = text(m.group(1)), text(m.group(2)), text(m.group(3))
    title, _, distance = name.rpartition(" · ")
    if not title:
        title, distance = name, ""
    return {"title": title, "distance": distance, "detail": rest.strip(" ·"), "date": date}


def strava_card(a: dict) -> str:
    ts = H - 2 * PAD
    x = PAD + ts + 16
    meta = " · ".join(p for p in (a["distance"], a["detail"]) if p)
    body = f"""  <svg x="{PAD}" y="{PAD}" width="{ts}" height="{ts}" viewBox="0 0 20 20" shape-rendering="crispEdges">{STRAVA_TILE}</svg>
  <circle cx="{x + 5}" cy="23" r="5" fill="{STRAVA}"/>
  <text x="{x + 18}" y="27" class="label">LAST ACTIVITY</text>
  <text x="{x}" y="64" class="title">{html.escape(clip(a["title"], 22))}</text>
  <text x="{x}" y="90" class="meta">{html.escape(clip(meta, 40))}</text>
  <text x="{x}" y="116" class="meta" fill="#8a8a8a">{html.escape(a["date"])}</text>"""
    return frame(f"Latest Strava activity: {a['title']}, {a['date']}", body)


def write(name: str, svg: str) -> None:
    out = ASSETS / name
    if out.exists() and out.read_text(encoding="utf-8") == svg:
        print(name, "no changes")
        return
    out.write_text(svg, encoding="utf-8")
    print(name, "updated")


def main() -> None:
    for name, build in (
        ("goodreads.svg", lambda: goodreads_card(book())),
        ("strava.svg", lambda: strava_card(activity())),
    ):
        try:
            write(name, build())
        except Exception as exc:  # noqa: BLE001 - keep yesterday's card rather than fail the job
            print(f"::warning::{name} not updated: {exc}")


if __name__ == "__main__":
    main()
