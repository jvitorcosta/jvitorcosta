# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Draw the README's Lately cards into assets/lately-*.svg: my website's Lately rows, in the profile's purple.

One card per account (Letterboxd, MyAnimeList, Goodreads and Strava, two by two), each in a dark and a light
version, saying what my website says. The data is what my site already saved (data/state.json on its `state`
branch), so this repo needs no tokens. The Spotify card above them is not drawn here: my now-playing service
draws it live (spotify-now-playing, api/card.py), with the same layout.

Run with: uv run scripts/lately_cards.py
If a source can't be read, that card is kept and the script still exits 0.
"""

import base64
import html
import json
import textwrap
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
STATE = "https://raw.githubusercontent.com/jvitorcosta/jvitorcosta.github.io/state/data/state.json"
UA = "Mozilla/5.0 (profile cards; +https://github.com/jvitorcosta/jvitorcosta)"
SANS = 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
# The header's and skyline's purple, so the page reads as one piece.
THEMES = {
    "dark": dict(bg="#150d24", edge="#3b2466", ink="#efe6ff", soft="#a99bc9", accent="#b57cff", chip="#2c1b4d", strava="#ff6a26"),
    "light": dict(bg="#f1e8ff", edge="#820ad1", ink="#2a0845", soft="#6b4a8f", accent="#820ad1", chip="#e2d2fa", strava="#b93a00"),
}
W, H, TEXT_X = 420, 136, 104


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - https URLs from my own data
        return resp.read()


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def day(iso: str) -> str:
    try:
        d = date.fromisoformat(iso[:10])
    except ValueError:
        return ""
    return f"{d:%b} {d.day}"


def duration(minutes: int) -> str:
    return f"{minutes} min" if minutes < 60 else f"{minutes // 60}h{minutes % 60:02d}"


def clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def data_uri(url: str) -> str:
    if url.startswith("data:image/"):
        return url
    if not url.startswith("https://"):
        return ""
    try:
        raw = get(url)
    except Exception as exc:  # noqa: BLE001 - the card is fine without a picture
        print(f"::warning::picture not read: {exc}")
        return ""
    kind = "png" if raw.startswith(b"\x89PNG") else "webp" if raw[8:12] == b"WEBP" else "jpeg"
    return f"data:image/{kind};base64,{base64.b64encode(raw).decode()}"


def pixel(text: str, x: float, y: float, size: float, fill: str) -> str:
    """Text in the site's pixel font, as paths: GitHub's images can't load a web font."""
    font = json.loads((ASSETS / "pixel-font.json").read_text(encoding="utf-8"))
    scale = size / font["unitsPerEm"]
    out, advance = [], 0
    for ch in text.upper():
        path, width = font["glyphs"].get(ch, font["glyphs"][" "])
        if path:
            out.append(f'<path transform="translate({advance} 0)" d="{path}"/>')
        advance += width
    return f'<g transform="translate({x} {y}) scale({scale} {-scale})" fill="{fill}">{"".join(out)}</g>'


def icon(name: str, x: float, y: float) -> str:
    """The site's 20x20 pixel tile for the account."""
    svg = (ASSETS / "icons" / f"{name}.svg").read_text(encoding="utf-8")
    inner = svg[svg.index(">") + 1 : svg.rindex("</svg>")]
    if "<title>" in inner:
        inner = inner[inner.index("</title>") + 8 :]
    return f'<svg x="{x}" y="{y}" width="30" height="30" viewBox="0 0 20 20" shape-rendering="crispEdges">{inner}</svg>'


@dataclass
class Card:
    """What one account's card says. Every card has the same slots, so they line up in the grid."""

    service: str
    label: str
    title: str
    detail: str
    note: str = ""  # an italic third line
    progress: float | None = None  # or a progress bar there
    link: str = ""  # or a link text there
    picture: str = ""
    emoji: str = ""


def draw(c: Card, mode: str) -> str:
    t = THEMES[mode]
    x = TEXT_X
    chars = int((W - x - 16) / 10.4)
    art = f'<rect x="16" y="16" width="70" height="104" rx="6" fill="{t["chip"]}"/>'
    if c.picture:
        art += (
            f'<image x="16" y="16" width="70" height="104" preserveAspectRatio="xMidYMid slice" '
            f'clip-path="url(#art)" href="{c.picture}"/>'
        )
    elif c.emoji:
        art += f'<text x="51" y="81" font-size="36" text-anchor="middle">{esc(c.emoji)}</text>'
    body = [pixel(c.label, x, 36, 11, t["accent"])]
    # A long title takes a second line and the rest moves down; the card keeps its height.
    lines = textwrap.wrap(c.title, chars, max_lines=2, placeholder="…")
    two = len(lines) > 1
    for i, line in enumerate(lines):
        body.append(
            f'<text x="{x}" y="{(58 if two else 66) + i * 20}" font-size="{17 if two else 19}" font-weight="700" '
            f'fill="{t["ink"]}">{esc(line)}</text>'
        )
    body.append(
        f'<text x="{x}" y="{98 if two else 91}" font-size="{14 if two else 15}" fill="{t["soft"]}">'
        f"{esc(clip(c.detail, chars + 8))}</text>"
    )
    third = 120 if two else 115
    if c.progress is not None:
        done = 200 * min(max(c.progress, 0), 1)
        body.append(
            f'<rect x="{x}" y="{third - 9}" width="200" height="8" rx="4" fill="{t["chip"]}"/>'
            f'<rect x="{x}" y="{third - 9}" width="{done:.0f}" height="8" rx="4" fill="{t["accent"]}"/>'
        )
    elif c.link:
        body.append(
            f'<text x="{x}" y="{third}" font-size="14" font-weight="700" fill="{t["strava"]}" '
            f'text-decoration="underline">{esc(c.link)}</text>'
        )
    elif c.note:
        body.append(
            f'<text x="{x}" y="{third}" font-size="14" font-style="italic" fill="{t["soft"]}">'
            f"{esc(clip(c.note, chars + 8))}</text>"
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
        f"<title>{esc(c.label.title())}: {esc(c.title)}</title>\n"
        f"<style>text{{font-family:{SANS}}}</style>\n"
        f'<defs><clipPath id="art"><rect x="16" y="16" width="70" height="104" rx="6"/></clipPath></defs>\n'
        f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="12" fill="{t["bg"]}" '
        f'stroke="{t["edge"]}" stroke-width="2"/>\n'
        f"{art}{''.join(body)}\n"
        f"{icon(c.service, W - 46, 16)}\n"
        "</svg>\n"
    )


# ---------- one builder per account ---------------------------------------------------------------


def letterboxd(state: dict) -> Card:
    film = state["film"]
    title = f"{film['title']} ({film['year']})" if film.get("year") else film["title"]
    rating = film.get("rating")
    stars = "" if rating is None else "★" * int(rating) + ("½" if rating - int(rating) >= 0.5 else "")
    marks = " ".join(m for m in (stars, "♥" if film.get("liked") else "") if m)
    detail = " · ".join(m for m in (marks, day(film.get("watched", ""))) if m)
    review = f"“{film['review']}”" if film.get("review") else ""
    return Card("letterboxd", "watched", title, detail, note=review, picture=data_uri(film.get("poster", "")))


def myanimelist(state: dict) -> Card:
    anime = state["anime"]
    progress = None
    if not anime.get("watching"):
        score = f"★ {anime['score']}/10" if anime.get("score") else ""
        detail = " · ".join(m for m in (score, day(anime.get("date", ""))) if m)
    elif anime.get("episodes"):
        detail = f"ep {anime['episode']} of {anime['episodes']}"
        progress = anime["episode"] / anime["episodes"]
    else:
        detail = f"ep {anime['episode']}"
    label = "watching" if anime.get("watching") else "finished"
    return Card(
        "myanimelist", label, anime["title"], detail, progress=progress, picture=data_uri(anime.get("cover", ""))
    )


def goodreads(state: dict) -> Card:
    book = state["book"]
    detail = book.get("author", "")
    progress = None
    if book.get("page") is not None and book.get("pages"):
        detail += f" · p. {book['page']} of {book['pages']}"
        progress = book["page"] / book["pages"]
    label = "finished" if book.get("finished") else "reading"
    return Card("goodreads", label, book["title"], detail, progress=progress, picture=data_uri(book.get("cover", "")))


def strava(state: dict) -> Card:
    act = state["activity"]
    if act.get("distance_km"):  # 0 or missing means no distance (weights, boxing): show the duration
        amount, parts = f"{act['distance_km']:.1f} km", [duration(act["moving_min"])]
    else:
        amount, parts = duration(act["moving_min"]), []
    # No-break spaces: a second line takes the last word along, never a lone "min" or "km".
    title = f"{act['title']}\xa0·\xa0" + amount.replace(" ", "\xa0")
    parts += [p for p in (act.get("detail"), day(act.get("date", ""))) if p]
    return Card(
        "strava", "exercised", title, " · ".join(parts), link="View on Strava", emoji=act.get("emoji", "")
    )


CARDS = (letterboxd, myanimelist, goodreads, strava)


def main() -> None:
    try:
        state = json.loads(get(STATE))
    except Exception as exc:  # noqa: BLE001 - keep yesterday's cards rather than fail the job
        print(f"::warning::site data not read, cards kept: {exc}")
        return
    for build in CARDS:
        name = build.__name__
        try:
            card = build(state)
            files = {f"lately-{name}-{mode}.svg": draw(card, mode) for mode in THEMES}
            for file, svg in files.items():
                (ASSETS / file).write_text(svg, encoding="utf-8", newline="\n")
                print("wrote", file)
        except Exception as exc:  # noqa: BLE001 - one broken source keeps only its own cards
            print(f"::warning::{name} cards not updated: {exc}")


if __name__ == "__main__":
    main()
