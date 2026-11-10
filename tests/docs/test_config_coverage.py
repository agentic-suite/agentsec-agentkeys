"""13.2 — every config key is documented; every documented key exists."""

from __future__ import annotations

from pathlib import Path

from agentkeys.config import _TOP_LEVEL, _TTL_CLASSES

DOC = Path(__file__).resolve().parents[2] / "docs" / "reference" / "config.md"


def test_every_config_key_is_documented() -> None:
    text = DOC.read_text(encoding="utf-8")
    expected = {
        "enforce_mode",
        "sink",
        "store.path",
        "clock.skew_tolerance",
        "ttl.<class>.floor",
        "ttl.<class>.ceiling",
        "backends[].id",
        "backends[].precedence",
        "bindings[].reference",
        "bindings[].audience",
        "bindings[].tool",
        "step_up.gated_classes",
        "step_up.timeout_seconds",
        "step_up.policy",
    }
    missing = sorted(key for key in expected if key not in text)
    assert missing == [], f"undocumented config keys: {missing}"
    for klass in _TTL_CLASSES:
        assert klass in text


def test_no_documented_top_level_key_is_unknown() -> None:
    text = DOC.read_text(encoding="utf-8")
    roots: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        cell = line.split("|")[1].strip().strip("`")
        root = cell.split(".")[0].split("[")[0].split("<")[0].strip("`").split()[0]
        if root in _TOP_LEVEL or root == "ttl":
            roots.add(root)
    assert roots
    assert roots <= (_TOP_LEVEL | {"ttl"})
