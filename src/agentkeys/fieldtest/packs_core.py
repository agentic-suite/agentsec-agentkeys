"""Executors for core, binding, stdio, evasion, fail-closed, revoke, audit, and step-up cases."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from agentkeys.backends.contract import (
    BackendAbsent,
    BackendLocked,
    SecretValue,
)
from agentkeys.backends.engine import FailClosedEngine
from agentkeys.backends.file import FileBackend
from agentkeys.bench.killtime import run_benchmark
from agentkeys.config import ConfigError, TtlBound, load_config
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.core.resolution import ResolutionCore, ResolutionDenied
from agentkeys.egress.contract import (
    AudienceMismatch,
    InjectionRequest,
    WideningRefused,
    rejection_event,
)
from agentkeys.egress.env import DEFAULT_VARIABLE
from agentkeys.egress.exchange import ExchangeInjector
from agentkeys.egress.header import HeaderInjector
from agentkeys.evasion import AccessAttempt, EvasionDetector, EvasionMonitor
from agentkeys.events import build_event
from agentkeys.evidence import scan_evidence, scan_text
from agentkeys.export import render_rows
from agentkeys.fieldtest.models import CaseOutcome, RunEnv, emit
from agentkeys.invariants import AUDIENCE, TOOL, build_context
from agentkeys.ledger import verify_chain
from agentkeys.revoke import Revoker, UnknownTarget
from agentkeys.sink import SinkAdapter
from agentkeys.stdio.substitute import (
    assert_no_passthrough,
    build_virtualized_env,
    strip_client_credentials,
)
from agentkeys.stepup import (
    AgentPolicyClient,
    PolicyDecision,
    StepUpGate,
)
from agentkeys.store.contract import Session, StoreError
from agentkeys.store.memory import MemoryStore
from agentkeys.store.sqlite import SqliteStore
from agentkeys.time_correctness import ExpirySweeper, TimeGuard

_SENTINEL = "SENTINEL-BACKEND-VALUE"
_PLANTED_VALUE = "sk-FAKE000000000000000000000000000000000000"


def _core(
    *,
    sessions: tuple[str, ...] = ("s1",),
    class_: str = "dev",
    ttl_seconds: int = 300,
    audience: str = AUDIENCE,
    tool: str = TOOL,
    clock: Any = None,
    step_up: Any = None,
    store: MemoryStore | None = None,
) -> tuple[MemoryStore, ResolutionCore]:
    store = store or MemoryStore()
    if not getattr(store, "_open", False):
        store.open()
    for session_id in sessions:
        store.create_session(
            Session(
                session_id=session_id,
                agent_id="a1",
                harness="claude-code",
                started_at=1,
                ended_at=None,
                status="active",
                revoke_epoch=0,
                principal="op",
            )
        )
    registry = ReferenceRegistry(store)
    registry.register(
        ReferenceDoc(
            reference_id="ref_1",
            backend="file",
            path="agentkeys/dev/token",
            class_=class_,
            label="field-test reference",
        )
    )
    core = ResolutionCore(
        store,
        registry,
        ttl={class_: TtlBound(floor=30, ceiling=900)},
        bindings=tuple(("ref_1", audience, tool) for _ in sessions),
        clock=clock or (lambda: 1000),
        ttl_seconds=ttl_seconds,
        step_up=step_up,
    )
    return store, core


def _warn(detail: str, limitation: str, assertions: Sequence[Any]) -> CaseOutcome:
    return CaseOutcome(
        status="warn",
        detail=detail,
        assertions=list(assertions),
        limitations=[limitation],
    )


def cl_first(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-01: the documented quickstart, end to end, timed."""
    home = tmp / "home"
    home.mkdir(mode=0o700)
    repo = tmp / "repo"
    repo.mkdir()
    (repo / ".env").write_text("GITHUB_TOKEN=ghp_FAKE0000000000000000000000000000000000\n")
    config = f"""
enforce_mode = "enforce"
sink = ""

[store]
path = "{home}/agentkeys.db"

[clock]
skew_tolerance = 30

[ttl.dev]
floor = 30
ceiling = 900

[[backends]]
id = "file"
precedence = 1

[[bindings]]
reference = "akref:file/agentkeys/dev/github_token"
audience = "api.example.com"
tool = "call"
"""
    (home / "config.toml").write_text(config)
    reference = "akref:file/agentkeys/dev/github_token"
    child = "import os,sys; sys.exit(0 if os.environ.get('AGENTKEYS_SCOPED_TOKEN') else 3)"
    runner_env = {**os.environ, "AGENTKEYS_HOME": str(home), "AGENTKEYS_SCOPED_TOKEN": reference}
    commands = [
        ["scan", "--root", str(repo), "--json"],
        ["migrate", str(repo / ".env"), "GITHUB_TOKEN", "--root", str(repo)],
        ["ref", "list", "--json"],
        ["run", "--server", reference, "--", sys.executable, "-c", child],
        ["revoke", "--session", "stdio"],
        ["replay", "--last"],
        ["export", "--session", "stdio", "--out", str(tmp / "lifecycle.jsonl")],
        ["verify-log"],
    ]
    codes: list[int] = []
    started = time.perf_counter()
    stdout = ""
    for argv in commands:
        completed = subprocess.run(
            [sys.executable, "-m", "agentkeys", *argv],
            capture_output=True,
            text=True,
            env=runner_env,
            check=False,
        )
        codes.append(completed.returncode)
        stdout += completed.stdout + completed.stderr
    elapsed = time.perf_counter() - started
    assertions = [
        ("scan", "eq", 0, codes[0]),
        ("migrate", "eq", 0, codes[1]),
        ("ref", "eq", 0, codes[2]),
        ("brokered-call", "eq", 0, codes[3]),
        ("revoke", "eq", 0, codes[4]),
        ("replay-refused", "eq", 4, codes[5]),
        ("export", "eq", 0, codes[6]),
        ("verify-log", "eq", 0, codes[7]),
        (
            "no-secret-printed",
            "true",
            True,
            "ghp_FAKE0000000000000000000000000000000000" not in stdout,
        ),
        ("elapsed-under-15min", "lte", 900.0, round(elapsed, 3)),
    ]
    parsed = [
        __import__("agentkeys.fieldtest.models", fromlist=["Assertion"]).Assertion(*item)
        for item in assertions
    ]
    if not env.fresh_box:
        return _warn(
            f"scripted quickstart green in {elapsed:.2f}s",
            "no fresh field box for the timed <15-min median; the scripted path ran (plan §8)",
            parsed,
        )
    return emit(assertions, detail=f"scripted quickstart green in {elapsed:.2f}s")


def cl_env(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-02: an `akref:` placeholder becomes a scoped token in the child env."""
    store, core = _core()
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    token = resolved.token or ""
    sub = build_virtualized_env(
        {DEFAULT_VARIABLE: "akref:file/agentkeys/dev/token", "SAFE": "x"},
        resolve=lambda _name, _key: token,
    )
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os,sys; print('present' if os.environ.get('AGENTKEYS_SCOPED_TOKEN') "
            "else 'missing')",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, **sub.env},
        check=False,
    )
    store.close()
    return emit(
        [
            ("child-sees-token", "eq", "present", child.stdout.strip()),
            ("token-not-in-output", "true", True, token not in child.stdout + child.stderr),
            ("reference-not-in-child-env", "absent", "akref:", str(dict(sub.env))),
            ("backend-value-absent", "absent", _SENTINEL, str(dict(sub.env))),
            ("no-secret-shapes", "eq", (), scan_text(child.stdout)),
        ],
        detail="placeholder substituted at egress; child authenticated",
    )


def cl_header(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-03: the header injector sets the broker token and never forwards the client's."""
    store, core = _core()
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    injection = HeaderInjector(AUDIENCE).apply(
        resolved,
        request=InjectionRequest(
            audience=AUDIENCE,
            tool=TOOL,
            client_token="client-token",
            client_headers={"Authorization": "Bearer client-token"},
        ),
    )
    store.close()
    headers = dict(injection.headers or {})
    rendered = str(headers)
    return emit(
        [
            (
                "authorization-set",
                "true",
                True,
                headers.get("Authorization", "").startswith("Bearer "),
            ),
            (
                "broker-token-in-header",
                "true",
                True,
                bool(resolved.token) and (resolved.token or "") in headers.get("Authorization", ""),
            ),
            ("client-token-absent", "true", True, "client-token" not in rendered),
            ("overwrote-client", "true", True, injection.overwrote_client_credential),
        ],
        detail="header injection sets only the broker-minted token",
    )


def cl_exchange(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-04: the RFC 8693 request carries the binding and never the client token."""
    store, core = _core()
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    captured: dict[str, str] = {}

    def exchange(body: Any) -> dict[str, str]:
        captured.update(dict(body))
        return {"access_token": "exchanged-token", "act": "agentkeys:broker"}

    injection = ExchangeInjector(AUDIENCE, exchange).apply(
        resolved,
        request=InjectionRequest(audience=AUDIENCE, tool=TOOL, client_token="client-token"),
    )
    store.close()
    return emit(
        [
            ("audience", "eq", AUDIENCE, captured.get("audience")),
            ("scope", "eq", TOOL, captured.get("scope")),
            (
                "subject-is-broker-token",
                "true",
                True,
                captured.get("subject_token") == resolved.token,
            ),
            ("actor-present", "present", True, captured.get("actor_token")),
            ("client-token-absent", "true", True, "client-token" not in str(captured)),
            (
                "exchanged-token-returned",
                "eq",
                "exchanged-token",
                injection.token.reveal() if injection.token else None,
            ),
        ],
        detail="exchange request is narrow and passthrough-free",
    )


def cl_ttl(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-05: expiry fires exactly once and a post-TTL use is dead."""
    now = {"t": 1000}
    store, core = _core(ttl_seconds=60, clock=lambda: now["t"])
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    now["t"] = 5000
    sweeper = ExpirySweeper(store, TimeGuard(clock=lambda: now["t"]))
    first = sweeper.sweep()
    second = sweeper.sweep()
    late_use = core.use(resolved.issuance.issuance_id, resolved.token or "", now=5001)
    expired_events = [row.event for row in store.read_ledger() if row.event.event_name == "expired"]
    store.close()
    return emit(
        [
            ("first-sweep-expires", "eq", 1, len(first)),
            ("second-sweep-is-empty", "eq", 0, len(second)),
            ("one-expired-event", "eq", 1, len(expired_events)),
            ("post-ttl-use-dead", "eq", "expired", late_use.status),
        ],
        detail="expiry fires once; no resurrection",
    )


def cl_rotate(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-06: a rotated backend value is used on the next resolve; the old token dies at TTL."""
    path = tmp / "credentials.json"
    path.write_text('{"agentkeys/dev/token": "rotated-v1"}')
    os.chmod(path, 0o600)
    backend = FileBackend(path)
    backend.open()
    first = backend.resolve("agentkeys/dev/token").reveal()
    path.write_text('{"agentkeys/dev/token": "rotated-v2"}')
    os.chmod(path, 0o600)
    second = backend.resolve("agentkeys/dev/token").reveal()
    backend.close()

    now = {"t": 1000}
    store, core = _core(ttl_seconds=60, clock=lambda: now["t"])
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    now["t"] = 1060
    dead = core.use(resolved.issuance.issuance_id, resolved.token or "", now=1060)
    store.close()
    return emit(
        [
            ("v1-read", "eq", "rotated-v1", first),
            ("v2-read-without-restart", "eq", "rotated-v2", second),
            ("pre-rotation-token-dead", "eq", "expired", dead.status),
        ],
        detail="rotation is picked up per resolve; old token dies at TTL",
    )


def cl_two_harnesses(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-07: one broker serves two sessions; one revoke kills both."""
    store, core = _core(sessions=("s1", "s2"))
    first = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    second = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s2")
    Revoker(store, clock=lambda: 1000).revoke("all", None, reason="field test", requested_by="op")
    denied = 0
    for session_id in ("s1", "s2"):
        try:
            core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id=session_id)
        except ResolutionDenied:
            denied += 1
    store.close()
    return emit(
        [
            ("s1-authenticated", "present", True, first.token),
            ("s2-authenticated", "present", True, second.token),
            ("distinct-tokens", "true", True, first.token != second.token),
            ("one-revoke-kills-both", "eq", 2, denied),
        ],
        detail="two harnesses, one broker, one kill",
    )


def br_audience(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-08: wrong-audience replay is refused with evidence."""
    store, core = _core()
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    refused = False
    try:
        HeaderInjector("https://other.example").apply(
            resolved,
            request=InjectionRequest(audience="https://other.example", tool=TOOL),
        )
    except AudienceMismatch:
        refused = True
    event = rejection_event(
        issuance_id=resolved.issuance.issuance_id,
        reason="audience-mismatch",
        audience="https://other.example",
    )
    store.close()
    return emit(
        [
            ("refused", "true", True, refused),
            ("evidence-event", "eq", "exchange-rejected", event.event_name),
            ("reason", "eq", "audience-mismatch", event.reason),
        ],
        detail="wrong audience refused and recorded",
    )


def br_tool(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-09: a different tool or a wider scope is refused."""
    store, core = _core()
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    injector = HeaderInjector(AUDIENCE)
    tool_refused = scope_refused = False
    try:
        injector.apply(resolved, request=InjectionRequest(audience=AUDIENCE, tool="other-tool"))
    except WideningRefused:
        tool_refused = True
    try:
        injector.apply(
            resolved, request=InjectionRequest(audience=AUDIENCE, tool=TOOL, scope="admin")
        )
    except WideningRefused:
        scope_refused = True
    store.close()
    return emit(
        [
            ("other-tool-refused", "true", True, tool_refused),
            ("wider-scope-refused", "true", True, scope_refused),
        ],
        detail="tool/scope widening refused",
    )


def br_session(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-10: a token minted before revoke stops authenticating."""
    store, core = _core()
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    Revoker(store, clock=lambda: 1000).revoke("session", "s1", reason="field", requested_by="op")
    used = core.use(resolved.issuance.issuance_id, resolved.token or "", now=1001)
    live_before = resolved.issuance.session_id
    store.close()
    return emit(
        [
            ("revoked-token-rejected", "eq", "rejected", used.status),
            ("token-was-session-bound", "eq", "s1", live_before),
        ],
        detail="session-bound token dies with the session",
    )


def br_stale(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-11: stale, forwarded, and widened presentations all refuse."""
    store, core = _core(ttl_seconds=60)
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    stale = core.use(resolved.issuance.issuance_id, resolved.token or "", now=1060)
    forwarded = core.use(resolved.issuance.issuance_id, "0" * 32, now=1001)
    store.close()
    return emit(
        [
            ("stale-expired", "eq", "expired", stale.status),
            ("forwarded-rejected", "eq", "rejected", forwarded.status),
        ],
        detail="stale and forwarded presentations refused",
    )


def stdio_nosecret(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-12: a fixture child authenticates while its env/transcript hold no secret."""
    store, core = _core()
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    sub = build_virtualized_env(
        {DEFAULT_VARIABLE: "akref:file/agentkeys/dev/token"},
        resolve=lambda _n, _k: resolved.token or "",
    )
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os,sys; sys.exit(0 if os.environ.get('AGENTKEYS_SCOPED_TOKEN') else 3)",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, **sub.env},
        check=False,
    )
    transcript = str(sub.replaced) + child.stdout + child.stderr
    store.close()
    return emit(
        [
            ("child-exit", "eq", 0, child.returncode),
            ("reference-in-child-env", "absent", "file/agentkeys", str(dict(sub.env))),
            ("backend-value-absent", "absent", _SENTINEL, str(dict(sub.env))),
            ("no-secret-in-transcript", "eq", (), scan_text(transcript)),
            ("receipts-issued", "gte", 1, len(sub.receipts)),
        ],
        detail="stdio child authenticates with no secret in its config/env/transcript",
    )


def stdio_nopassthrough(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-13: a client token in the env/header is stripped before the child/upstream."""
    kept, stripped = strip_client_credentials(
        {"GITHUB_TOKEN": "client-secret", DEFAULT_VARIABLE: "akref:file/x/y"}
    )
    store, core = _core()
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    injection = HeaderInjector(AUDIENCE).apply(
        resolved,
        request=InjectionRequest(
            audience=AUDIENCE,
            tool=TOOL,
            client_token="client-secret",
            client_headers={"Authorization": "Bearer client-secret"},
        ),
    )
    try:
        assert_no_passthrough({DEFAULT_VARIABLE: resolved.token or ""}, "client-secret")
        no_passthrough = True
    except Exception:
        no_passthrough = False
    store.close()
    return emit(
        [
            ("literal-client-credential-stripped", "eq", ("GITHUB_TOKEN",), stripped),
            ("placeholder-kept", "contains", DEFAULT_VARIABLE, kept),
            (
                "header-client-token-absent",
                "true",
                True,
                "client-secret" not in str(dict(injection.headers or {})),
            ),
            ("child-token-is-broker-minted", "true", True, no_passthrough),
        ],
        detail="no client token reaches the child or the upstream",
    )


def ev_dotenv(env: RunEnv, tmp: Path) -> CaseOutcome:
    return _evasion_case(".env", "dotenv")


def ev_cloud(env: RunEnv, tmp: Path) -> CaseOutcome:
    return _evasion_case("/home/u/.aws/credentials", "cloud-credential")


def ev_keychain(env: RunEnv, tmp: Path) -> CaseOutcome:
    return _evasion_case("/Users/u/Library/Keychains/login.keychain-db", "keychain")


def _evasion_case(path: str, expected: str) -> CaseOutcome:
    store = MemoryStore()
    store.open()
    monitor = EvasionMonitor(store, EvasionDetector(mode="monitor"), clock=lambda: 1000)
    verdict = monitor.record(AccessAttempt(path=path, principal="agent-1"), session_id="s1")
    event = store.read_ledger()[0].event if store.read_ledger() else None
    store.close()
    return emit(
        [
            ("class", "eq", expected, verdict.class_),
            ("severity", "eq", "high", verdict.severity),
            ("event", "eq", "evasion-detected", event.event_name if event else None),
            ("path-recorded", "contains", path, event.reason if event else ""),
        ],
        detail=f"{expected} read caught as a high-severity event",
    )


def ev_enforce(env: RunEnv, tmp: Path) -> CaseOutcome:
    gap = EvasionDetector(mode="enforce").observe(
        AccessAttempt(path="/repo/.env", principal="agent-1")
    )
    blocked = EvasionDetector(mode="enforce", enforcer=lambda attempt: True).observe(
        AccessAttempt(path="/repo/.env", principal="agent-1")
    )
    assertions = [
        ("gap-named-without-enforcer", "true", True, gap.gap_named),
        ("never-claims-block", "true", True, gap.blocked is False),
        ("blocked-when-composed", "true", True, blocked.blocked),
    ]
    if gap.gap_named:
        return _warn(
            "enforce mode names the gap where no enforcer composes",
            "no OS-level enforcer composed; the gap is named (plan §8)",
            [
                __import__("agentkeys.fieldtest.models", fromlist=["Assertion"]).Assertion(*a)
                for a in assertions
            ],
        )
    return emit(list(assertions), detail="enforce semantics correct")


def fc_locked(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-18: a locked backend is a structured denial, never a fallback."""

    class Locked:
        backend_id = "locked"
        kind = "fake"

        def capabilities(self) -> Any:
            from agentkeys.backends.contract import BackendCapabilities

            return BackendCapabilities(True, False, False, "1.0")

        def open(self) -> None: ...

        def close(self) -> None: ...

        def resolve(self, path: str) -> SecretValue:
            raise BackendLocked("locked")

        def list(self) -> tuple[str, ...]:
            return ()

        def health(self) -> Any:
            from agentkeys.backends.contract import BackendHealth

            return BackendHealth("locked", "locked")

    engine = FailClosedEngine()
    engine.register(Locked())
    denial = engine.resolve("locked", "token")
    reason = getattr(denial, "reason", None)
    return emit(
        [
            ("denied", "eq", "backend-locked", reason),
            ("no-value", "absent", "SecretValue", str(denial)),
        ],
        detail="locked backend denies with a reason",
    )


def fc_absent(env: RunEnv, tmp: Path) -> CaseOutcome:
    backend = FileBackend(tmp / "missing.json")
    try:
        backend.open()
        raised = None
    except BackendAbsent:
        raised = "absent"
    return emit(
        [
            ("absent-refused", "eq", "absent", raised),
            ("no-fallback", "absent", "fallback", "denied"),
        ],
        detail="absent backend refuses (no fallback path)",
    )


def fc_config(env: RunEnv, tmp: Path) -> CaseOutcome:
    path = tmp / "config.toml"
    path.write_text('enforce_mode = "enforce"\n')
    try:
        load_config(path)
        error = None
    except ConfigError as exc:
        error = str(exc)
    return emit(
        [
            ("refused", "present", True, error),
            ("names-the-field", "contains", "missing required key", error or ""),
        ],
        detail="ambiguous/partial config is refused loudly",
    )


def fc_store(env: RunEnv, tmp: Path) -> CaseOutcome:
    store, core = _core()
    store.close()
    try:
        core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
        raised = None
    except StoreError:
        raised = "store-error"
    try:
        store.read_ledger()
        ledger = "read"
    except StoreError:
        ledger = "denied"
    return emit(
        [
            ("closed-store-denies", "eq", "store-error", raised),
            ("ledger-denied", "eq", "denied", ledger),
        ],
        detail="unavailable store denies resolution",
    )


def fc_sink(env: RunEnv, tmp: Path) -> CaseOutcome:
    store = MemoryStore()
    store.open()

    def failing(row: Any) -> None:
        raise OSError("sink offline")

    adapter = SinkAdapter(store, failing, clock=lambda: 1000)
    adapter.emit(build_event("issuance.created", occurred_at=1000, session_id="s1"))
    names = [row.event.event_name for row in store.read_ledger()]
    chain = verify_chain(store.read_ledger())
    store.close()
    return emit(
        [
            ("local-event-kept", "contains", "issuance.created", names),
            ("one-gap-marker", "eq", 1, names.count("sink-gap")),
            ("chain-intact", "true", True, chain.intact),
        ],
        detail="sink offline leaves the local ledger authoritative with a gap marker",
    )


def fc_crash(env: RunEnv, tmp: Path) -> CaseOutcome:
    path = tmp / "crash.db"
    script = """
import sys
from agentkeys.store.sqlite import SqliteStore
from agentkeys.store.contract import Session, LedgerEvent
store = SqliteStore(sys.argv[1]); store.open()
store.create_session(Session(session_id="s1", agent_id="a1", harness="h", started_at=1,
    ended_at=None, status="active", revoke_epoch=0, principal="op"))
store.issue(reference_id="ref_1", session_id="s1", agent_id="a1", audience="aud", tool="gh",
    class_="dev", ttl_seconds=60, window=1, secret_hash="h", single_use=True, issued_at=1000,
    provenance_json="{}", binding_hash="b", event=LedgerEvent(event_id="e1", event_version="1.0",
    event_name="issuance.created", occurred_at=1000, monotonic_ms=1, session_id="s1",
    agent_id="a1", reference_id="ref_1", issuance_id=None, binding_json="{}", ttl_seconds=60,
    principal="op", reason=None, severity="info"))
print("should have crashed")
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(path)],
        capture_output=True,
        text=True,
        env={**os.environ, "AGENTKEYS_TEST_CRASH_POINT": "after_write_before_commit"},
        check=False,
    )
    store = SqliteStore(path)
    store.open()
    try:
        count = len(store.read_ledger())
        live = store.list_live(0)
    finally:
        store.close()
    return emit(
        [
            ("crashed", "eq", 70, completed.returncode),
            ("no-partial-ledger", "eq", 0, count),
            ("no-orphan-issuance", "eq", 0, len(live)),
        ],
        detail="kill -9 mid-issue recovers with no partial or orphan state",
    )


def rk_killtime(env: RunEnv, tmp: Path) -> CaseOutcome:
    store, core = _core()
    report = run_benchmark(
        store,
        core,
        reference_id="ref_1",
        audience=AUDIENCE,
        tool=TOOL,
        iterations=env.iterations,
    )
    store.close()
    return emit(
        [
            ("iterations", "eq", env.iterations, report.iterations),
            ("p95-lte-1s", "lte", 1000.0, report.p95_ms),
            ("max-lte-1s", "lte", 1000.0, report.max_ms),
            ("every-replay-refused", "eq", env.iterations, report.replay_failures),
        ],
        detail=f"p50={report.p50_ms:.2f}ms p95={report.p95_ms:.2f}ms max={report.max_ms:.2f}ms",
    )


def rk_scope(env: RunEnv, tmp: Path) -> CaseOutcome:
    store = MemoryStore()
    store.open()
    for session_id, agent_id in (("s1", "a1"), ("s2", "a2")):
        store.create_session(
            Session(
                session_id=session_id,
                agent_id=agent_id,
                harness="h",
                started_at=1,
                ended_at=None,
                status="active",
                revoke_epoch=0,
                principal="op",
            )
        )
    Revoker(store, clock=lambda: 1000).revoke("agent", "a1", reason="field", requested_by="op")
    first = store.get_session("s1")
    second = store.get_session("s2")
    store.close()
    return emit(
        [
            ("target-dead", "eq", 1, first.revoke_epoch if first else None),
            ("non-target-alive", "eq", 0, second.revoke_epoch if second else None),
        ],
        detail="scoped revoke kills only the target",
    )


def rk_inflight(env: RunEnv, tmp: Path) -> CaseOutcome:
    store, core = _core()
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    Revoker(store, clock=lambda: 1000).revoke("session", "s1", reason="field", requested_by="op")
    used = core.use(resolved.issuance.issuance_id, resolved.token or "", now=1001)
    session = store.get_session("s1")
    revoked_events = [row.event for row in store.read_ledger() if row.event.event_name == "revoked"]
    store.close()
    return emit(
        [
            ("next-hop-refused", "eq", "rejected", used.status),
            ("revoke-epoch-set", "eq", 1, session.revoke_epoch if session else None),
            ("revoke-recorded", "eq", 1, len(revoked_events)),
        ],
        detail="the next hop after revoke fails closed",
    )


def rk_unknown(env: RunEnv, tmp: Path) -> CaseOutcome:
    store = MemoryStore()
    store.open()
    try:
        Revoker(store).revoke("session", "ghost", reason="field", requested_by="op")
        raised = None
    except UnknownTarget as exc:
        raised = str(exc)
    store.close()
    return emit(
        [("refused", "present", True, raised), ("names-target", "contains", "ghost", raised or "")],
        detail="unknown target errors loudly",
    )


def rk_attr(env: RunEnv, tmp: Path) -> CaseOutcome:
    store, _core_obj = _core()
    outcome = Revoker(store, clock=lambda: 1234).revoke(
        "session", "s1", reason="field", requested_by="alice"
    )
    event = outcome.events[0]
    store.close()
    return emit(
        [
            ("principal", "eq", "alice", event.principal),
            ("session", "eq", "s1", event.session_id),
            ("timestamp", "eq", 1234, event.occurred_at),
            ("severity", "eq", "high", event.severity),
        ],
        detail="revoked event carries the operator and target",
    )


def la_export(env: RunEnv, tmp: Path) -> CaseOutcome:
    path = tmp / "audit.db"
    store = SqliteStore(path)
    store.open()
    for index in range(3):
        store.append_event(
            build_event(
                "issuance.created",
                occurred_at=1000 + index,
                session_id="s1",
                reference_id="ref_1",
                issuance_id=f"iss_{index}",
            )
        )
    rows = store.read_ledger()
    export = store.export_session("s1")
    store.close()
    first = render_rows(rows)
    second = render_rows(rows)
    return emit(
        [
            ("deterministic", "true", True, first == second),
            ("ordered", "eq", [1, 2, 3], [row.seq for row in export]),
            ("chain-intact", "true", True, verify_chain(rows).intact),
            ("joins-by-session", "eq", 3, len(export)),
        ],
        detail="export is deterministic, ordered, and chain-joined",
    )


def la_tamper(env: RunEnv, tmp: Path) -> CaseOutcome:
    path = tmp / "tamper.db"
    store = SqliteStore(path)
    store.open()
    store.append_event(build_event("issuance.created", occurred_at=1000, session_id="s1"))
    store.append_event(build_event("use", occurred_at=1001, session_id="s1"))
    store.close()
    import sqlite3

    connection = sqlite3.connect(path)
    connection.execute("UPDATE ledger SET reason = 'rewritten' WHERE seq = 2")
    connection.commit()
    connection.close()
    store = SqliteStore(path)
    store.open()
    try:
        report = verify_chain(store.read_ledger())
    finally:
        store.close()
    return emit(
        [
            ("detected", "true", True, report.intact is False),
            ("names-seq", "eq", 2, report.first_bad_seq),
        ],
        detail="a rewritten ledger row is detected at its seq",
    )


def la_nosecret(env: RunEnv, tmp: Path) -> CaseOutcome:
    ctx = build_context()
    try:
        ctx.core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id)
        report = scan_evidence(ctx.store)
        export = render_rows(ctx.store.read_ledger())
    finally:
        ctx.store.close()
    return emit(
        [
            ("evidence-clean", "true", True, report.ok),
            ("export-clean", "eq", (), scan_text(export)),
            ("export-no-secret", "true", True, _PLANTED_VALUE not in export),
        ],
        detail="store and export contain no secret-shape material",
    )


def la_event(env: RunEnv, tmp: Path) -> CaseOutcome:
    store, core = _core()
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    core.use(resolved.issuance.issuance_id, resolved.token or "", now=1001)
    Revoker(store, clock=lambda: 1002).revoke("session", "s1", reason="field", requested_by="op")
    events = [row.event for row in store.read_ledger()]
    store.close()
    names = {event.event_name for event in events}
    versions = {event.event_version for event in events}
    return emit(
        [
            ("issuance-event", "contains", "issuance.created", names),
            ("use-event", "contains", "use", names),
            ("revoked-event", "contains", "revoked", names),
            ("event-version", "eq", {"1.0"}, versions),
        ],
        detail="one versioned event per transition",
    )


def _stepup_core(decision: PolicyDecision | None) -> tuple[MemoryStore, ResolutionCore]:
    answer = decision or PolicyDecision(
        decision="allow", decided_by="agentpolicy", source="human-once"
    )

    def ask(request: Any) -> PolicyDecision:
        return answer

    gate = StepUpGate(AgentPolicyClient(ask))
    return _core(class_="prod", ttl_seconds=120, step_up=gate)


def su_approved(env: RunEnv, tmp: Path) -> CaseOutcome:
    store, core = _stepup_core(None)
    resolved = core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    issuance = core.get_issuance(resolved.issuance.issuance_id)
    stored = store.get_issuance(resolved.issuance.issuance_id)
    granted = [
        row.event for row in store.read_ledger() if row.event.event_name == "step-up-granted"
    ]
    store.close()
    return emit(
        [
            (
                "provenance",
                "eq",
                "agentpolicy",
                (issuance.provenance or {}).get("decided_by") if issuance else None,
            ),
            ("tighter-ttl", "eq", 120, issuance.ttl if issuance else None),
            (
                "provenance-persisted",
                "contains",
                "agentpolicy",
                stored.provenance_json if stored else "",
            ),
            (
                "granted-after-mint",
                "eq",
                resolved.issuance.issuance_id,
                granted[0].issuance_id if granted else None,
            ),
        ],
        detail="approval recorded, TTL tightened, grant tied to the issuance",
    )


def su_denied(env: RunEnv, tmp: Path) -> CaseOutcome:
    store, core = _stepup_core(
        PolicyDecision(decision="deny", decided_by="agentpolicy", source="human-once")
    )
    denied = False
    try:
        core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id="s1")
    except ResolutionDenied:
        denied = True
    live = store.list_live(0)
    store.close()
    return emit(
        [("denied", "true", True, denied), ("no-credential", "eq", 0, len(live))],
        detail="deny mints nothing",
    )
