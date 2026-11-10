"""13.T — every local Markdown link in the docs resolves."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")


def _markdown_files() -> list[Path]:
    files = list((ROOT / "docs").rglob("*.md"))
    files.extend([ROOT / "README.md", ROOT / "SECURITY.md", ROOT / "CONTRIBUTING.md"])
    return [path for path in files if path.is_file()]


def test_local_doc_links_resolve() -> None:
    broken: list[str] = []
    for path in _markdown_files():
        text = path.read_text(encoding="utf-8")
        for target in LINK.findall(text):
            link = target.split("#", 1)[0].strip()
            if not link or link.startswith(SKIP_PREFIXES):
                continue
            if link.startswith("<") and link.endswith(">"):
                link = link[1:-1]
            resolved = (path.parent / link).resolve()
            if ROOT not in resolved.parents and resolved != ROOT:
                # A source citation to a sibling repository: not a local page.
                continue
            if not resolved.exists():
                broken.append(f"{path.relative_to(ROOT)} -> {target}")
    assert broken == [], "\n".join(broken)
