"""Parse `field-test/v0.1.0/cases.yaml` (a small, frozen YAML subset; no third-party parser)."""

from __future__ import annotations

import os
from pathlib import Path

from agentkeys.fieldtest.models import Case

__all__ = ["CASES_PATH", "load_cases", "load_cases_text"]


def _value(raw: str) -> object:
    text = raw.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return tuple(item.strip() for item in inner.split(",") if item.strip())
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    if text in {"null", "~", ""}:
        return None
    return text


def load_cases_text(text: str) -> tuple[Case, ...]:
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip() or line.strip() == "cases:":
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current is not None:
                entries.append(current)
            current = {}
            stripped = stripped[2:]
        if current is None or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        current[key.strip()] = _value(value)
    if current is not None:
        entries.append(current)

    cases: list[Case] = []
    for entry in entries:
        scenario = entry.get("scenario")
        env_raw = entry.get("env") or ()
        env = env_raw if isinstance(env_raw, (tuple, list)) else (env_raw,)
        cases.append(
            Case(
                id=str(entry["id"]),
                pack=str(entry["pack"]),
                scenario=None if scenario is None else str(scenario),
                klass=str(entry.get("class", "P/F")),
                env=tuple(str(item) for item in env),
                driver=str(entry.get("driver", "")),
            )
        )
    return tuple(cases)


def load_cases(path: str | Path) -> tuple[Case, ...]:
    return load_cases_text(Path(path).read_text(encoding="utf-8"))


def field_root() -> Path:
    """The repo root holding `field-test/` (override with `AGENTKEYS_FIELD_ROOT` in containers)."""
    override = os.environ.get("AGENTKEYS_FIELD_ROOT")
    return Path(override).resolve() if override else Path(__file__).resolve().parents[3]


CASES_PATH = field_root() / "field-test" / "v0.1.0" / "cases.yaml"
