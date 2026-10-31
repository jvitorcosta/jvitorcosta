# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Rewrite the "recently pushed" section of README.md from the GitHub API.

Run with: uv run scripts/update_readme.py
Env: GITHUB_TOKEN (optional locally, set in Actions), GH_USER (default: jvitorcosta).
"""

import json
import os
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

USER = os.environ.get("GH_USER", "jvitorcosta")
README = Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!-- RECENT:START -->", "<!-- RECENT:END -->"
LIMIT = 5
HIDDEN = {"fraud-alert-explainer"}


def fetch_repos() -> list[dict]:
    url = f"https://api.github.com/users/{USER}/repos?type=owner&sort=pushed&per_page=30"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token := os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https URL
        return json.load(resp)


def when(pushed_at: str, now: datetime) -> str:
    dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
    return f"{dt:%b} {dt.day}" if dt.year == now.year else f"{dt:%b %Y}"


def render(repos: list[dict]) -> str:
    now = datetime.now(UTC)
    picked = [
        r
        for r in repos
        if not r["fork"] and not r["archived"] and r["name"] != USER and r["name"] not in HIDDEN
    ][:LIMIT]
    lines = []
    for r in picked:
        desc = f": {r['description'].strip()}" if r.get("description") else ""
        lines.append(f"- [{r['name']}]({r['html_url']}){desc} · <sub>{when(r['pushed_at'], now)}</sub>")
    return "\n".join(lines)


def main() -> None:
    text = README.read_text(encoding="utf-8")
    block = f"{START}\n{render(fetch_repos())}\n{END}"
    new = re.sub(rf"{re.escape(START)}.*?{re.escape(END)}", lambda _: block, text, flags=re.S)
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()
