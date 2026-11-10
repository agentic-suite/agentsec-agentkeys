"""0.4 (gate) — close the fail-closed branches of the config validator."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentkeys.config import ConfigError, agentkeys_home, load_config
from tests.test_config import VALID, _write

INLINE_STORE = 'store = { path = "{home}/agentkeys.db" }\n'
INLINE_CLOCK = "clock = { skew_tolerance = 30 }\n"
HEAD = 'enforce_mode = "enforce"\nsink = ""\n'


@pytest.mark.parametrize(
    ("old", "new", "match"),
    [
        ("floor = 30", "floor = 0", r"ttl\.dev\.floor"),
        ("[ttl.prod]", "[ttl.weird]", r"ttl\.weird"),
        ('path = "{home}/agentkeys.db"', "path = 7", "store.path"),
        ("skew_tolerance = 30", "skew_tolerance = -1", "clock.skew_tolerance"),
        ("precedence = 2", "precedence = 0", r"backends\[1\]\.precedence"),
        ("[clock]", "[store.bogus]\nx = 1\n\n[clock]", "store.bogus"),
    ],
)
def test_invalid_values_fail_closed(tmp_path: Path, old: str, new: str, match: str) -> None:
    assert old in VALID
    path = _write(tmp_path, VALID.replace(old, new, 1))
    with pytest.raises(ConfigError, match=match):
        load_config(path)


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ('enforce_mode = 5\nsink = ""\n', "enforce_mode"),
        ('enforce_mode = "enforce"\nsink = 5\n', "sink must be a string"),
        (HEAD + 'store = "x"\n', "store must be a table"),
        (HEAD + INLINE_STORE + "clock = {}", "clock.skew_tolerance"),
        (HEAD + INLINE_STORE + 'clock = "x"', "clock must be a table"),
    ],
)
def test_early_shape_errors_fail_closed(tmp_path: Path, text: str, match: str) -> None:
    path = _write(tmp_path, text)
    with pytest.raises(ConfigError, match=match):
        load_config(path)


TTL = "ttl = { dev = { floor = 30, ceiling = 900 } }\n"
BACKENDS = 'backends = [{ id = "keychain", precedence = 1 }]\n'


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("ttl = 5\n", "ttl"),
        ("ttl = {}\n", "at least one class"),
        ("ttl = { dev = 5 }\n", "ttl.dev must be a table"),
        (TTL + "backends = 5\n", "backends"),
        (TTL + 'backends = ["x"]\n', r"backends\[0\] must be a table"),
        (TTL + BACKENDS + "bindings = 5\n", "bindings must be an array"),
        (TTL + BACKENDS + 'bindings = ["x"]\n', r"bindings\[0\] must be a table"),
        (TTL + BACKENDS, "bindings"),
    ],
)
def test_late_shape_errors_fail_closed(tmp_path: Path, text: str, match: str) -> None:
    header = HEAD + INLINE_STORE + INLINE_CLOCK
    path = _write(tmp_path, header + text)
    with pytest.raises(ConfigError, match=match):
        load_config(path)


def test_empty_backend_id_fails_closed(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID.replace('id = "keychain"', 'id = ""'))
    with pytest.raises(ConfigError, match=r"backends\[0\]\.id"):
        load_config(path)


def test_duplicate_binding_fails_closed(tmp_path: Path) -> None:
    binding = (
        '\n[[bindings]]\nreference = "agentkeys/dev/example-api-token"\n'
        'audience = "api.github.com"\ntool = "gh"\n'
    )
    path = _write(tmp_path, VALID + binding)
    with pytest.raises(ConfigError, match="duplicate bindings"):
        load_config(path)


def test_secret_inside_a_list_is_caught(tmp_path: Path) -> None:
    secret = "ghp_0123456789abcdefghijklmnopqrstuvwxyz"
    path = _write(
        tmp_path,
        VALID.replace('reference = "agentkeys/dev/example-api-token"', f'reference = "{secret}"'),
    )
    with pytest.raises(ConfigError, match=r"literal secret.*bindings\[0\]\.reference"):
        load_config(path)


def test_unknown_nested_flag_key_is_named(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID.replace("precedence = 1", "precedence = 1\nbogus = true"))
    with pytest.raises(ConfigError, match=r"unknown key: backends\[0\]\.bogus"):
        load_config(path)


def test_agentkeys_home_defaults_and_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("AGENTKEYS_HOME", raising=False)
    assert agentkeys_home() == tmp_path / ".agentkeys"
    assert agentkeys_home({"AGENTKEYS_HOME": str(tmp_path / "x")}) == tmp_path / "x"
