# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Refresh the two generated blocks of README.md from the GitHub API and the Letterboxd card.

- NOW: "building <the repo I pushed to last> · watching <last film from assets/letterboxd.svg>".
- PROJECTS: my curated projects, each with the date of its last push.

Run with: uv run scripts/update_readme.py   (after scripts/letterboxd_card.py)
Env: GITHUB_TOKEN (optional locally, set in Actions), GH_USER (default: jvitorcosta).
"""

import html
import json
import os
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

USER = os.environ.get("GH_USER", "jvitorcosta")
ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
LETTERBOXD = ROOT / "assets" / "letterboxd.svg"
HIDDEN = {"fraud-alert-explainer", USER}

# name, what it is (first person), stack, optional live link
PROJECTS = [
    ("car-cyberdeck", "a taste of Pokémon nostalgia on my car's dashboard", "ESP32, C++", None),
    ("car-can-lab", "listening to my car's CAN bus over Bluetooth to find its signals", "ESP32, Python", None),
    ("or-solver-streamlit", "SolvedOR, my bachelor thesis: an app that teaches Operations Research", "Python, OR-Tools", "https://solvedor.streamlit.app"),
    ("timeseries-analysis-streamlit", "shows where a daily forecast goes wrong: by series, weekday, holiday and benchmark", "Python, Plotly", "https://forecast-error-analysis.streamlit.app"),
    ("ask-vitor", "ask a local LLM about me; it answers only from my CV and says so when it doesn't know", "FastAPI, Ollama", None),
    ("python-uv-claude-template", "how I start every Python project", "Python, uv", None),
]


def fetch_repos() -> list[dict]:
    url = f"https://api.github.com/users/{USER}/repos?type=owner&sort=pushed&per_page=50"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token := os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https URL
        return json.load(resp)


def when(pushed_at: str, now: datetime) -> str:
    dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
    return f"{dt:%b} {dt.day}" if dt.year == now.year else f"{dt:%b %Y}"


def projects_block(by_name: dict[str, dict], now: datetime) -> str:
    lines = []
    for name, blurb, stack, live in PROJECTS:
        repo = by_name.get(name)
        url = repo["html_url"] if repo else f"https://github.com/{USER}/{name}"
        pushed = f" · pushed {when(repo['pushed_at'], now)}" if repo else ""
        link = f" · [live]({live})" if live else ""
        lines.append(f"- **[{name}]({url})**: {blurb} · <sub>{stack}{pushed}</sub>{link}")
    return "\n".join(lines)


def watching() -> str | None:
    if not LETTERBOXD.exists():
        return None
    m = re.search(r"<title>Last watched on Letterboxd: (.+?)</title>", LETTERBOXD.read_text(encoding="utf-8"))
    return html.unescape(m.group(1)) if m else None


def now_block(repos: list[dict]) -> str:
    building = next((r for r in repos if not r["fork"] and not r["archived"] and r["name"] not in HIDDEN), None)
    parts = []
    if building:
        parts.append(f"🔨 building [{building['name']}]({building['html_url']})")
    parts.append("🎧 listening: live card below")
    if film := watching():
        parts.append(f"🎬 watching {film}")
    return "**Now** · " + " · ".join(parts)


def swap(text: str, tag: str, body: str) -> str:
    start, end = f"<!-- {tag}:START -->", f"<!-- {tag}:END -->"
    block = f"{start}\n{body}\n{end}"
    return re.sub(rf"{re.escape(start)}.*?{re.escape(end)}", lambda _: block, text, flags=re.S)


def main() -> None:
    now = datetime.now(UTC)
    repos = fetch_repos()
    text = README.read_text(encoding="utf-8")
    new = swap(text, "NOW", now_block(repos))
    new = swap(new, "PROJECTS", projects_block({r["name"]: r for r in repos}, now))
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()
