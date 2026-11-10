"""Validation and edge branches for the M6-M10 modules and the step-up config."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentkeys.backends.contract import BackendAmbiguous, BackendUnavailable
from agentkeys.config import ConfigError, load_config
from agentkeys.correlation import correlate
from agentkeys.evasion import AccessAttempt, EvasionDetector, EvasionMonitor, classify_path
from agentkeys.events import build_event, validate_event
from agentkeys.migrate import FileSecretWriter
from agentkeys.recipes import get_recipe, render_mcp_wiring, validate_wiring
from agentkeys.revoke import Revoker
from agentkeys.stepup import AgentPolicyClient, PolicyDecision, StepUpGate
from agentkeys.store.contract import LedgerRow
from agentkeys.store.memory import MemoryStore
from agentkeys.tamper import EnumerationSignal, IntegrityVerdict

CONFIG = """
enforce_mode = "enforce"
sink = ""
{extra}

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

[[bindings]]
reference = "ref_1"
audience = "api.github.com"
tool = "gh"
"""


def _config(tmp_path: Path, extra: str = "") -> Path:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    path = home / "config.toml"
    path.write_text(CONFIG.replace("{home}", str(home)).replace("{extra}", extra), encoding="utf-8")
    return path


def test_step_up_defaults_gate_prod(tmp_path: Path) -> None:
    config = load_config(_config(tmp_path))
    assert config.gated_classes == ("prod",)
    assert config.step_up_timeout == 30
    assert config.policy == ""


def test_step_up_can_be_configured(tmp_path: Path) -> None:
    config = load_config(
        _config(
            tmp_path,
            '\n[step_up]\ngated_classes = ["prod", "staging"]\n'
            'timeout_seconds = 60\npolicy = "unix:/run/agentpolicy.sock"\n',
        )
    )
    assert config.gated_classes == ("prod", "staging")
    assert config.step_up_timeout == 60
    assert config.policy == "unix:/run/agentpolicy.sock"


@pytest.mark.parametrize(
    ("extra", "match"),
    [
        ("\nstep_up = 1\n", "must be a table"),
        ("\n[step_up]\ngated_classes = []\n", "non-empty"),
        ('\n[step_up]\ngated_classes = ["nope"]\n', "gated_classes"),
        ("\n[step_up]\ntimeout_seconds = 0\n", "timeout_seconds"),
        ("\n[step_up]\ntimeout_seconds = true\n", "timeout_seconds"),
        ("\n[step_up]\npolicy = 1\n", "policy"),
        ("\n[step_up]\nunknown = 1\n", "unknown key"),
    ],
)
def test_step_up_fails_closed(tmp_path: Path, extra: str, match: str) -> None:
    with pytest.raises(ConfigError, match=match):
        load_config(_config(tmp_path, extra))


def test_evasion_rejects_an_unknown_mode() -> None:
    with pytest.raises(ValueError, match="mode"):
        EvasionDetector(mode="sometimes")


def test_evasion_classifies_keyrings_and_env_exports() -> None:
    assert classify_path("/home/u/.local/share/keyrings/login.keyring") == "keychain"
    assert classify_path("/repo/agentkeys_home") == "env-export"


def test_a_monitor_records_the_attempt_agent() -> None:
    store = MemoryStore()
    store.open()
    monitor = EvasionMonitor(store, EvasionDetector(mode="monitor"))
    monitor.record(AccessAttempt(path="/repo/.env", principal="op", session_id="s1"), agent_id="a1")
    event = store.read_ledger()[0].event
    assert event.session_id == "s1"
    assert event.agent_id == "a1"


def test_enumeration_signal_validates_its_window() -> None:
    with pytest.raises(ValueError, match="threshold"):
        EnumerationSignal(threshold=0)
    with pytest.raises(ValueError, match="window"):
        EnumerationSignal(window_seconds=0)
    signal = EnumerationSignal(threshold=1)
    assert signal.observe("ref_x") is True
    signal.reset()
    assert signal.observe("ref_x") is True


def test_an_integrity_verdict_carries_the_digest() -> None:
    verdict = IntegrityVerdict(True, None, "abc")
    assert verdict.digest == "abc"


def test_the_gate_knows_which_classes_are_gated() -> None:
    gate = StepUpGate(AgentPolicyClient(lambda request: PolicyDecision("allow", "p", "s")))
    assert gate.is_gated("prod") is True
    assert gate.is_gated("dev") is False


def test_events_validate_the_schema_version() -> None:
    event = build_event("use", occurred_at=1)
    bad = event.__class__(**{**event.__dict__, "event_version": "2.0"})
    with pytest.raises(Exception, match="event_version"):
        validate_event(bad)


@pytest.mark.parametrize(
    ("call", "match"),
    [
        (lambda revoker: revoker.revoke("all", "s1", reason="r", requested_by="o"), "no target"),
        (lambda revoker: revoker.revoke("session", None, reason="r", requested_by="o"), "requires"),
    ],
)
def test_revoke_argument_guards(call: object, match: str) -> None:
    store = MemoryStore()
    store.open()
    with pytest.raises(ValueError, match=match):
        call(Revoker(store))  # type: ignore[operator]


def test_correlation_skips_rows_without_a_session() -> None:
    store = MemoryStore()
    store.open()
    store.append_event(build_event("use", occurred_at=1))
    rows: tuple[LedgerRow, ...] = store.read_ledger()
    assert correlate(rows) == ()


@pytest.mark.parametrize(
    "wiring",
    [
        {"mcpServers": {}},
        {"mcpServers": {"a": {}, "b": {}}},
        {"mcpServers": {"a": {"command": "agentkeys", "args": "run"}}},
        {"mcpServers": {"a": {"command": "agentkeys", "args": ["run"]}}},
        {"mcpServers": {"a": {"command": "agentkeys", "args": ["run", "--server"]}}},
        {
            "mcpServers": {
                "a": {"command": "agentkeys", "args": ["run", "--server", "akref:x/y"], "env": 1}
            }
        },
        {
            "mcpServers": {
                "a": {
                    "command": "agentkeys",
                    "args": ["run", "--server", "akref:x/y"],
                    "env": {"TOKEN": 1},
                }
            }
        },
        {
            "mcpServers": {
                "a": {
                    "command": "agentkeys",
                    "args": ["run", "--server", "akref:x/y"],
                    "env": {"TOKEN": "literal"},
                }
            }
        },
    ],
)
def test_broken_wirings_are_refused(wiring: object) -> None:
    with pytest.raises(Exception, match="recipe|wiring|mcpServers|args|env|command|server"):
        validate_wiring(get_recipe("generic-mcp"), wiring)  # type: ignore[arg-type]


def test_rendered_wiring_is_valid() -> None:
    validate_wiring(get_recipe("generic-mcp"), render_mcp_wiring(get_recipe("generic-mcp")))


def test_file_writer_refuses_a_conflicting_slot(tmp_path: Path) -> None:
    writer = FileSecretWriter(tmp_path / "creds.json")
    writer.write("slot", "one")
    with pytest.raises(BackendAmbiguous):
        writer.write("slot", "two")


def test_file_writer_read_missing_and_delete(tmp_path: Path) -> None:
    writer = FileSecretWriter(tmp_path / "creds.json")
    with pytest.raises(BackendUnavailable):
        writer.read("missing")
    writer.write("slot", "one")
    writer.delete("slot")
    assert writer.read.__name__ == "read"
    with pytest.raises(BackendUnavailable):
        writer.read("slot")
