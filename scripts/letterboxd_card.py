# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Draw assets/letterboxd.svg: the last film logged on Letterboxd, read from the public RSS feed.

Run with: uv run scripts/letterboxd_card.py
Env: LETTERBOXD_USER (default: zubu).

The poster is embedded as base64 because GitHub does not load external images inside an SVG.
If the feed can't be read, the existing card is kept and the script still exits 0.
"""

import base64
import html
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

USER = os.environ.get("LETTERBOXD_USER", "zubu")
OUT = Path(__file__).resolve().parent.parent / "assets" / "letterboxd.svg"
NS = {"letterboxd": "https://letterboxd.com"}
UA = "Mozilla/5.0 (profile card; +https://github.com/jvitorcosta/jvitorcosta)"

# Same frame as the Spotify card next to it (novatorem, dark theme).
W, H = 540, 135
PAD = 7
POSTER_H = H - 2 * PAD
POSTER_W = round(POSTER_H * 2 / 3)
BG = "#181414"
ORANGE, GREEN, BLUE = "#ff8000", "#00e054", "#40bcf4"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https URLs
        return resp.read()


def latest_film() -> dict:
    root = ET.fromstring(get(f"https://letterboxd.com/{USER}/rss/"))
    for item in root.iter("item"):
        title = item.findtext("letterboxd:filmTitle", namespaces=NS)
        if not title:  # lists and other non-film entries
            continue
        desc = item.findtext("description") or ""
        poster = re.search(r'<img src="([^"]+)"', desc)
        review = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", desc)).split())
        rating = item.findtext("letterboxd:memberRating", namespaces=NS)
        watched = item.findtext("letterboxd:watchedDate", namespaces=NS)
        return {
            "title": title,
            "year": item.findtext("letterboxd:filmYear", namespaces=NS) or "",
            "rating": float(rating) if rating else None,
            "liked": item.findtext("letterboxd:memberLike", namespaces=NS) == "Yes",
            "rewatch": item.findtext("letterboxd:rewatch", namespaces=NS) == "Yes",
            "watched": date.fromisoformat(watched) if watched else None,
            # A diary entry without a review has "Watched on ..." as its only text.
            "review": "" if review.startswith("Watched on ") else review,
            "poster": poster.group(1).replace("-0-600-0-900-", "-0-230-0-345-") if poster else None,
        }
    raise ValueError("no films in the feed")


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def stars(rating: float) -> str:
    return "★" * int(rating) + ("½" if rating % 1 else "")


def render(film: dict) -> str:
    x = PAD + POSTER_W + 14
    if film["poster"]:
        data = base64.b64encode(get(film["poster"])).decode()
        poster = (
            f'<image x="{PAD}" y="{PAD}" width="{POSTER_W}" height="{POSTER_H}" clip-path="url(#poster)" '
            f'preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{data}"/>'
        )
    else:
        poster = f'<rect x="{PAD}" y="{PAD}" width="{POSTER_W}" height="{POSTER_H}" rx="4" fill="#2c3440"/>'

    meta = [film["year"]] if film["year"] else []
    if film["rewatch"]:
        meta.append("rewatch")
    if film["watched"]:
        meta.append(f"watched {film['watched']:%b} {film['watched'].day}")
    rating = stars(film["rating"]) if film["rating"] else ""
    heart = f'<tspan fill="{ORANGE}">{" " if rating else ""}♥</tspan>' if film["liked"] else ""
    review = (
        f'<text x="{x}" y="126" class="review">“{html.escape(clip(film["review"], 52))}”</text>'
        if film["review"]
        else ""
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <title>Last watched on Letterboxd: {html.escape(film["title"])}</title>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}
    .label {{ font-size: 12px; font-weight: 600; letter-spacing: 1.5px; fill: #9ab; }}
    .title {{ font-size: 26px; font-weight: 700; fill: url(#ink); }}
    .meta {{ font-size: 15px; fill: #9ab; }}
    .stars {{ font-size: 20px; fill: {GREEN}; }}
    .review {{ font-size: 14px; font-style: italic; fill: #789; }}
  </style>
  <defs>
    <clipPath id="poster"><rect x="{PAD}" y="{PAD}" width="{POSTER_W}" height="{POSTER_H}" rx="4"/></clipPath>
    <linearGradient id="ink" x1="0" x2="1">
      <stop offset="0" stop-color="{ORANGE}"/><stop offset="1" stop-color="{GREEN}"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" rx="5" fill="{BG}"/>
  {poster}
  <circle cx="{x + 5}" cy="23" r="5" fill="{ORANGE}"/>
  <circle cx="{x + 17}" cy="23" r="5" fill="{GREEN}"/>
  <circle cx="{x + 29}" cy="23" r="5" fill="{BLUE}"/>
  <text x="{x + 42}" y="27" class="label">LAST WATCHED</text>
  <text x="{x}" y="61" class="title">{html.escape(clip(film["title"], 26))}</text>
  <text x="{x}" y="84" class="meta">{html.escape(" · ".join(meta))}</text>
  <text x="{x}" y="107" class="stars">{rating}{heart}</text>
  {review}
</svg>
"""


def main() -> None:
    try:
        svg = render(latest_film())
    except Exception as exc:  # noqa: BLE001 - keep yesterday's card rather than fail the job
        print(f"::warning::Letterboxd card not updated: {exc}")
        return
    OUT.parent.mkdir(exist_ok=True)
    if OUT.exists() and OUT.read_text(encoding="utf-8") == svg:
        print("No changes")
        return
    OUT.write_text(svg, encoding="utf-8")
    print(f"Card updated: {OUT.name}")


if __name__ == "__main__":
    main()
