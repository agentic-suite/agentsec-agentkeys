"""0.4 — the references-only config model: valid config loads; anything else fails closed."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentkeys.config import Config, ConfigError, discover_config_path, load_config

VALID = """
enforce_mode = "enforce"
sink = ""

[store]
path = "{home}/agentkeys.db"

[clock]
skew_tolerance = 30

[ttl.dev]
floor = 30
ceiling = 900

[ttl.prod]
floor = 30
ceiling = 300

[[backends]]
id = "keychain"
precedence = 1

[[backends]]
id = "file"
precedence = 2

[[bindings]]
reference = "agentkeys/dev/example-api-token"
audience = "api.github.com"
tool = "gh"
"""


def _write(tmp_path: Path, text: str, name: str = "config.toml") -> Path:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    path = home / name
    path.write_text(text.replace("{home}", str(home)), encoding="utf-8")
    return path


def test_valid_config_loads_typed_values(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID)
    config = load_config(path)
    assert isinstance(config, Config)
    assert config.enforce_mode == "enforce"
    assert config.sink == ""
    assert config.store_path == path.parent / "agentkeys.db"
    assert config.clock_skew_tolerance == 30
    assert [b.id for b in config.backends] == ["keychain", "file"]
    assert config.backends[0].precedence == 1
    assert config.ttl["dev"].floor == 30
    assert config.ttl["dev"].ceiling == 900
    assert config.bindings[0].audience == "api.github.com"
    assert config.bindings[0].tool == "gh"


def test_missing_config_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.toml")


def test_malformed_toml_fails_closed(tmp_path: Path) -> None:
    path = _write(tmp_path, "enforce_mode = ")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config(path)


def test_unknown_key_names_the_dotted_path(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID.replace('enforce_mode = "enforce"', 'enforce_mode = "enforce"\nsurprise = "x"'))
    with pytest.raises(ConfigError, match=r"unknown key: surprise"):
        load_config(path)


def test_missing_required_key_is_named(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID.replace('enforce_mode = "enforce"\n', ""))
    with pytest.raises(ConfigError, match="enforce_mode"):
        load_config(path)


def test_bad_enforce_mode_fails_closed(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID.replace('"enforce"', '"maybe"'))
    with pytest.raises(ConfigError, match="enforce_mode"):
        load_config(path)


def test_ttl_ceiling_below_floor_fails_closed(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID.replace("ceiling = 900", "ceiling = 10"))
    with pytest.raises(ConfigError, match=r"ttl\.dev\.ceiling"):
        load_config(path)


def test_duplicate_backend_precedence_is_ambiguous(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID.replace("precedence = 2", "precedence = 1"))
    with pytest.raises(ConfigError, match="precedence"):
        load_config(path)


def test_duplicate_backend_id_is_ambiguous(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID.replace('id = "file"', 'id = "keychain"'))
    with pytest.raises(ConfigError, match=r"backends\[1\]\.id"):
        load_config(path)


def test_store_path_may_not_be_an_existing_directory(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID.replace("agentkeys.db", "adir"))
    (path.parent / "adir").mkdir()
    with pytest.raises(ConfigError, match="store.path"):
        load_config(path)


def test_literal_secret_is_rejected_without_echoing_it(tmp_path: Path) -> None:
    secret = "ghp_0123456789abcdefghijklmnopqrstuvwxyz"
    path = _write(tmp_path, VALID.replace('sink = ""', f'sink = "{secret}"'))
    with pytest.raises(ConfigError) as excinfo:
        load_config(path)
    message = str(excinfo.value)
    assert "sink" in message
    assert secret not in message


# Assembled at runtime so no token-shaped literal is committed (push protection scans file text).
_FAKE_SLACK = "xox" + "b-" + "0" * 10 + "-" + "notatoken"


@pytest.mark.parametrize(
    "secret",
    [
        "sk-0123456789abcdefghijklmnopqrstuvwxyz",
        "AKIAIOSFODNN7EXAMPLE",
        _FAKE_SLACK,
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJl",
    ],
)
def test_known_credential_shapes_are_rejected(tmp_path: Path, secret: str) -> None:
    path = _write(tmp_path, VALID.replace('sink = ""', f'sink = "{secret}"'))
    with pytest.raises(ConfigError, match="literal secret"):
        load_config(path)


def test_empty_binding_field_fails_closed(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID.replace('audience = "api.github.com"', 'audience = ""'))
    with pytest.raises(ConfigError, match=r"bindings\[0\]\.audience"):
        load_config(path)


def test_discovery_prefers_explicit_then_home_then_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    explicit = tmp_path / "explicit.toml"
    assert discover_config_path(explicit, env={}) == explicit

    monkeypatch.delenv("AGENTKEYS_HOME", raising=False)
    home = tmp_path / "akhome"
    assert discover_config_path(None, env={"AGENTKEYS_HOME": str(home)}) == home / "config.toml"

    monkeypatch.setenv("HOME", str(tmp_path))
    assert discover_config_path(None, env={}) == tmp_path / ".agentkeys" / "config.toml"


def test_agentkeys_home_default_is_expandable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTKEYS_HOME", str(tmp_path / "ak"))
    monkeypatch.setenv("HOME", str(tmp_path))
    assert discover_config_path(None) == tmp_path / "ak" / "config.toml"