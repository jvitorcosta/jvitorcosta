# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Draw the README's Lately cards into assets/lately-*.svg, in the style of my website's Lately box.

One card per account: Spotify, Letterboxd, MyAnimeList, Goodreads, Strava. The data is what my site
already saved (data/state.json on its `state` branch), so this repo needs no tokens; the song also asks
my now-playing endpoint for the latest track. A card is a still image, so the song reads "listened".

Run with: uv run scripts/lately_cards.py
If a source can't be read, that card is kept and the script still exits 0.
"""

import base64
import html
import json
import textwrap
import urllib.request
from datetime import date
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
STATE = "https://raw.githubusercontent.com/jvitorcosta/jvitorcosta.github.io/state/data/state.json"
SONG = "https://spotify-now-playing-ashen-two.vercel.app/api/now-playing.json"
UA = "Mozilla/5.0 (profile cards; +https://github.com/jvitorcosta/jvitorcosta)"
SANS = 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
# The website's Nubank-purple palette (.pal-nu in its site.css).
BOX, INK, SHADOW, SOFT, HP, STRAVA = "#f7f0e1", "#2a0845", "#4a0478", "#e9dcc2", "#ffb703", "#c43d00"
W, TEXT_X, WRAP = 420, 88, 29


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


def wrap(text: str, width: int = WRAP, lines: int = 2) -> list[str]:
    return textwrap.wrap(text, width, max_lines=lines, placeholder="…")


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


def pixel(text: str, x: float, y: float, size: float, fill: str = INK) -> str:
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


def icon(name: str, y: float) -> str:
    """The site's 20x20 pixel tile for the account, framed in ink."""
    svg = (ASSETS / "icons" / f"{name}.svg").read_text(encoding="utf-8")
    inner = svg[svg.index(">") + 1 : svg.rindex("</svg>")]
    if "<title>" in inner:
        inner = inner[inner.index("</title>") + 8 :]
    return (
        f'<svg x="354" y="{y}" width="42" height="42" viewBox="0 0 20 20" shape-rendering="crispEdges">{inner}</svg>'
        f'<rect x="354" y="{y}" width="42" height="42" fill="none" stroke="{INK}" stroke-width="2"/>'
    )


def card(
    service: str,
    label: str,
    title: str,
    details: list[str],
    *,
    picture: str = "",
    emoji: str = "",
    tall: bool = False,
    review: str = "",
    progress: float | None = None,
    link_text: str = "",
) -> str:
    """One website-style box: picture, pixel label, bold title, detail lines, the account's pixel tile."""
    body = [pixel(label, TEXT_X, 32, 12)]
    y = 56
    for line in wrap(title):
        body.append(f'<text x="{TEXT_X}" y="{y}" font-size="17" font-weight="700">{esc(line)}</text>')
        y += 22
    for line in details:
        body.append(f'<text x="{TEXT_X}" y="{y}" font-size="15">{esc(line)}</text>')
        y += 21
    if review:
        for line in wrap(f"“{review}”", WRAP + 4):
            body.append(f'<text x="{TEXT_X}" y="{y}" font-size="15" font-style="italic">{esc(line)}</text>')
            y += 21
    if progress is not None:
        body.append(
            f'<rect x="{TEXT_X}" y="{y - 10}" width="160" height="10" fill="{BOX}" stroke="{INK}" stroke-width="2"/>'
            f'<rect x="{TEXT_X + 1}" y="{y - 9}" width="{158 * min(max(progress, 0), 1):.0f}" height="8" fill="{HP}"/>'
        )
        y += 16
    if link_text:
        body.append(
            f'<text x="{TEXT_X}" y="{y}" font-size="15" font-weight="700" fill="{STRAVA}" '
            f'text-decoration="underline">{esc(link_text)}</text>'
        )
        y += 21
    th = 78 if tall else 54
    height = max(y + 2, th + 40)
    ty = (height - 6 - th) / 2
    art = f'<rect x="18" y="{ty}" width="54" height="{th}" fill="{SOFT}"/>'
    if picture:
        art += (
            f'<image x="18" y="{ty}" width="54" height="{th}" preserveAspectRatio="xMidYMid slice" '
            f'href="{picture}"/>'
        )
    elif emoji:
        art += f'<text x="45" y="{ty + th / 2 + 10}" font-size="28" text-anchor="middle">{esc(emoji)}</text>'
    art += f'<rect x="18" y="{ty}" width="54" height="{th}" fill="none" stroke="{INK}" stroke-width="3"/>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}">\n'
        f"<title>{esc(label.title())}: {esc(title)}</title>\n"
        f"<style>text{{font-family:{SANS}}}</style>\n"
        f'<rect x="8" y="8" width="410" height="{height - 8}" rx="4" fill="{SHADOW}"/>\n'
        f'<rect x="2" y="2" width="410" height="{height - 8}" rx="4" fill="{BOX}" stroke="{INK}" stroke-width="3"/>\n'
        f'<g fill="{INK}">{art}{"".join(body)}</g>\n'
        f"{icon(service, (height - 6 - 42) / 2)}\n"
        "</svg>\n"
    )


# ---------- one builder per account ---------------------------------------------------------------


def spotify(state: dict) -> str:
    try:
        song = json.loads(get(SONG))
        if not song.get("title"):
            raise ValueError("no song")
    except Exception as exc:  # noqa: BLE001 - the site's saved song is the fallback
        print(f"::warning::live song not read: {exc}")
        song = state["song"]
    picture = data_uri(song.get("cover_data") or song.get("cover") or "")
    return card("spotify", "listened", song["title"], wrap(song.get("artist", ""), WRAP + 4, 1), picture=picture)


def letterboxd(state: dict) -> str:
    film = state["film"]
    title = f"{film['title']} ({film['year']})" if film.get("year") else film["title"]
    rating = film.get("rating")
    stars = "" if rating is None else "★" * int(rating) + ("½" if rating - int(rating) >= 0.5 else "")
    marks = " ".join(m for m in (stars, "♥" if film.get("liked") else "") if m)
    detail = " · ".join(m for m in (marks, day(film.get("watched", ""))) if m)
    return card(
        "letterboxd", "watched", title, [detail], picture=data_uri(film.get("poster", "")), tall=True,
        review=film.get("review", ""),
    )


def myanimelist(state: dict) -> str:
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
    return card(
        "myanimelist", "watching" if anime.get("watching") else "finished", anime["title"], [detail],
        picture=data_uri(anime.get("cover", "")), tall=True, progress=progress,
    )


def goodreads(state: dict) -> str:
    book = state["book"]
    details = wrap(book.get("author", ""), WRAP + 4, 1)
    progress = None
    if book.get("page") is not None and book.get("pages"):
        details.append(f"p. {book['page']} of {book['pages']}")
        progress = book["page"] / book["pages"]
    return card(
        "goodreads", "finished" if book.get("finished") else "reading", book["title"], details,
        picture=data_uri(book.get("cover", "")), tall=True, progress=progress,
    )


def strava(state: dict) -> str:
    act = state["activity"]
    if act.get("distance_km"):  # 0 or missing means no distance: show the duration in the title
        title, parts = f"{act['title']} · {act['distance_km']:.1f} km", [duration(act["moving_min"])]
    else:
        title, parts = f"{act['title']} · {duration(act['moving_min'])}", []
    parts += [p for p in (act.get("detail"), day(act.get("date", ""))) if p]
    return card(
        "strava", "moved", title, wrap(" · ".join(parts), WRAP + 4),
        emoji=act.get("emoji", ""), link_text="View on Strava",
    )


CARDS = (spotify, letterboxd, myanimelist, goodreads, strava)


def main() -> None:
    try:
        state = json.loads(get(STATE))
    except Exception as exc:  # noqa: BLE001 - keep yesterday's cards rather than fail the job
        print(f"::warning::site data not read, cards kept: {exc}")
        return
    for build in CARDS:
        name = f"lately-{build.__name__}.svg"
        try:
            (ASSETS / name).write_text(build(state), encoding="utf-8", newline="\n")
            print("wrote", name)
        except Exception as exc:  # noqa: BLE001 - one broken source keeps only its own card
            print(f"::warning::{name} not updated: {exc}")


if __name__ == "__main__":
    main()
