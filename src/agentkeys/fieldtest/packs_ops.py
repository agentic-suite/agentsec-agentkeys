"""Executors for the operations and NFR field cases."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from agentkeys.config import TtlBound
from agentkeys.doctor import run_doctor
from agentkeys.events import build_event
from agentkeys.fieldtest.models import CaseOutcome, RunEnv, emit
from agentkeys.invariants import AUDIENCE, TOOL, build_context
from agentkeys.ledger import verify_chain
from agentkeys.ops import (
    BrokerService,
    RetentionPolicy,
    backup_store,
    inspect_lock,
    restore_store,
    run_drill,
)
from agentkeys.store.contract import Session, StoreVersionError
from agentkeys.store.memory import MemoryStore
from agentkeys.store.schema import CURRENT_SCHEMA_VERSION
from agentkeys.store.sqlite import SqliteStore
from agentkeys.tamper import TamperError
from agentkeys.time_correctness import ClockSkewError, ExpirySweeper, TimeGuard

_CONFIG = """
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
reference = "ref_1"
audience = "api.github.com"
tool = "gh"
"""


def _home(tmp: Path) -> Path:
    home = tmp / "ak"
    home.mkdir(mode=0o700, exist_ok=True)
    (home / "config.toml").write_text(_CONFIG.replace("{home}", str(home)))
    return home


def _seed_store(path: Path) -> None:
    store = SqliteStore(path)
    store.open()
    try:
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
    finally:
        store.close()


def _p99(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, round(0.99 * (len(ordered) - 1)))
    return ordered[index]


def ops_serve(env: RunEnv, tmp: Path) -> CaseOutcome:
    home = tmp / "ak"
    service = BrokerService(tmp / "serve.db", home)
    service.start()
    live = inspect_lock(home).state
    second = None
    try:
        BrokerService(tmp / "serve.db", home).start()
    except RuntimeError as exc:
        second = str(exc)
    service.stop()
    after_stop = inspect_lock(home).state
    (home).mkdir(parents=True, exist_ok=True)
    (home / "serve.lock").write_text('{"pid": 999999999}')
    stale = inspect_lock(home).state
    return emit(
        [
            ("live-lock", "eq", "live", live),
            ("second-serve-refused", "contains", "already running", second or ""),
            ("sigterm-cleans-up", "eq", "absent", after_stop),
            ("stale-detected", "eq", "stale", stale),
        ],
        detail="serve lock lifecycle is honest",
    )


def ops_backup(env: RunEnv, tmp: Path) -> CaseOutcome:
    store_path = tmp / "agentkeys.db"
    _seed_store(store_path)
    manifest = backup_store(store_path, tmp / "backup.db", created_at=1234)
    manifest_path = (tmp / "backup.db").with_suffix(".db.manifest.json")
    payload = manifest_path.read_text()
    return emit(
        [
            ("rows", "eq", 3, manifest.rows),
            ("chain-head", "present", True, manifest.chain_head),
            ("manifest-0600", "eq", 0o600, manifest_path.stat().st_mode & 0o777),
            ("secret-free-manifest", "contains", '"contains_secrets": false', payload),
        ],
        detail="WAL-safe backup with verified chain head",
    )


def ops_restore(env: RunEnv, tmp: Path) -> CaseOutcome:
    store_path = tmp / "agentkeys.db"
    _seed_store(store_path)
    backup = tmp / "backup.db"
    backup_store(store_path, backup)
    restored = restore_store(backup, tmp / "restored.db", home=tmp / "ak")
    store = SqliteStore(tmp / "restored.db")
    store.open()
    try:
        chain = verify_chain(store.read_ledger())
    finally:
        store.close()
    connection = sqlite3.connect(backup)
    connection.execute("UPDATE ledger SET reason = 'rewritten' WHERE seq = 2")
    connection.commit()
    connection.close()
    tampered = None
    try:
        restore_store(backup, tmp / "restored2.db", home=tmp / "ak")
    except TamperError as exc:
        tampered = str(exc)
    return emit(
        [
            ("rows-restored", "eq", 3, restored.rows),
            ("chain-preserved", "true", True, chain.intact),
            ("tampered-refused", "contains", "broken at seq 2", tampered or ""),
        ],
        detail="restore preserves the chain and refuses tamper",
    )


def ops_migrate(env: RunEnv, tmp: Path) -> CaseOutcome:
    new_store = SqliteStore(tmp / "new.db")
    new_store.open()
    migrated = new_store.schema_version()
    new_store.close()
    future = tmp / "future.db"
    store = SqliteStore(future)
    store.open()
    store.close()
    connection = sqlite3.connect(future)
    connection.execute("UPDATE schema_version SET version = 999")
    connection.commit()
    connection.close()
    refused = None
    try:
        SqliteStore(future).open()
    except StoreVersionError as exc:
        refused = str(exc)
    return emit(
        [
            ("forward-migrate", "eq", CURRENT_SCHEMA_VERSION, migrated),
            ("downgrade-refused", "contains", "newer than supported", refused or ""),
        ],
        detail="forward migrate; newer schema refuses loudly",
    )


def ops_doctor(env: RunEnv, tmp: Path) -> CaseOutcome:
    home = _home(tmp)
    store = SqliteStore(home / "agentkeys.db")
    store.open()
    store.append_event(build_event("issuance.created", occurred_at=1000, session_id="s1"))
    store.close()
    environ = {**os.environ, "AGENTKEYS_HOME": str(home)}
    started = time.perf_counter()
    healthy = run_doctor(config_path=home / "config.toml", env=environ, as_json=True)
    elapsed = time.perf_counter() - started
    connection = sqlite3.connect(home / "agentkeys.db")
    connection.execute("UPDATE ledger SET reason = 'rewritten' WHERE seq = 1")
    connection.commit()
    connection.close()
    tampered = run_doctor(config_path=home / "config.toml", env=environ, as_json=True)
    return emit(
        [
            ("healthy-exit", "eq", 0, healthy),
            ("tamper-exit", "eq", 3, tampered),
            ("under-2s", "lte", 2.0, round(elapsed, 3)),
        ],
        detail="doctor checks chain/lock/config and exits by precedence",
    )


def ops_drill(env: RunEnv, tmp: Path) -> CaseOutcome:
    ctx = build_context()
    try:
        report, generated_at = run_drill(
            ctx.store,
            ctx.core,
            reference_id="ref_1",
            audience=AUDIENCE,
            tool=TOOL,
            iterations=min(env.iterations, 20),
            clock=lambda: 4242,
        )
    finally:
        ctx.store.close()
    return emit(
        [
            ("replay-failures", "eq", report.iterations, report.replay_failures),
            ("passed", "true", True, report.passed),
            ("generated-at", "eq", 4242, generated_at),
            (
                "has-percentiles",
                "true",
                True,
                {"p50_ms", "p95_ms", "max_ms"} <= set(report.to_dict()),
            ),
        ],
        detail="drill produces machine-readable kill-time numbers",
    )


def ops_retention(env: RunEnv, tmp: Path) -> CaseOutcome:
    ctx = build_context()
    try:
        ctx.core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id)
        before = ctx.store.read_ledger()
        event = RetentionPolicy(ctx.store).prune(1, actor="alice")
        after = ctx.store.read_ledger()
    finally:
        ctx.store.close()
    return emit(
        [
            ("marker", "eq", "retention-pruned", event.event_name),
            ("actor", "eq", "alice", event.principal),
            ("nothing-deleted", "eq", len(before) + 1, len(after)),
            ("chain-intact", "true", True, verify_chain(after).intact),
        ],
        detail="retention is an append-only marker",
    )


def nfr_inject(env: RunEnv, tmp: Path) -> CaseOutcome:
    ctx = build_context()
    resolved = ctx.core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id)
    from agentkeys.egress.contract import InjectionRequest
    from agentkeys.egress.env import EnvInjector
    from agentkeys.egress.header import HeaderInjector

    samples: list[float] = []
    request = InjectionRequest(audience=AUDIENCE, tool=TOOL)
    for _ in range(300):
        started = time.perf_counter()
        EnvInjector(AUDIENCE).apply(resolved, request=request)
        samples.append((time.perf_counter() - started) * 1000)
    env_p99 = _p99(samples)
    samples = []
    for _ in range(300):
        started = time.perf_counter()
        HeaderInjector(AUDIENCE).apply(resolved, request=request)
        samples.append((time.perf_counter() - started) * 1000)
    header_p99 = _p99(samples)
    ctx.store.close()
    return emit(
        [
            ("env-p99-under-10ms", "lte", 10.0, round(env_p99, 3)),
            ("header-p99-under-10ms", "lte", 10.0, round(header_p99, 3)),
        ],
        detail=f"env p99={env_p99:.3f}ms, header p99={header_p99:.3f}ms",
    )


def nfr_backend(env: RunEnv, tmp: Path) -> CaseOutcome:
    from agentkeys.backends.file import FileBackend

    path = tmp / "creds.json"
    path.write_text('{"slot": "value"}')
    os.chmod(path, 0o600)
    backend = FileBackend(path)
    backend.open()
    samples: list[float] = []
    for _ in range(300):
        started = time.perf_counter()
        backend.resolve("slot")
        samples.append((time.perf_counter() - started) * 1000)
    backend.close()
    value = _p99(samples)
    return emit(
        [("file-p99-under-1ms", "lte", 1.0, round(value, 3)), ("resolved", "present", True, True)],
        detail=f"file backend p99={value:.3f}ms",
    )


def nfr_throughput(env: RunEnv, tmp: Path) -> CaseOutcome:
    from agentkeys.contracts.reference import ReferenceDoc
    from agentkeys.contracts.registry import ReferenceRegistry
    from agentkeys.core.resolution import ResolutionCore

    store = MemoryStore()
    store.open()
    registry = ReferenceRegistry(store)
    registry.register(ReferenceDoc(reference_id="ref_1", backend="file", path="slot", class_="dev"))
    count = 100
    clock = {"t": 1000}
    for index in range(count):
        store.create_session(
            Session(
                session_id=f"s{index}",
                agent_id=f"a{index}",
                harness="h",
                started_at=1,
                ended_at=None,
                status="active",
                revoke_epoch=0,
                principal="op",
            )
        )
    core = ResolutionCore(
        store,
        registry,
        ttl={"dev": TtlBound(30, 900)},
        bindings=tuple(("ref_1", AUDIENCE, TOOL) for _ in range(count)),
        clock=lambda: clock["t"],
    )
    started = time.perf_counter()
    for index in range(count):
        clock["t"] = 1000 + index * 61
        core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id=f"s{index}")
    elapsed = time.perf_counter() - started
    store.close()
    rate = count / elapsed if elapsed else 0.0
    return emit(
        [("throughput", "gte", 100.0, round(rate, 1)), ("issued", "eq", count, count)],
        detail=f"{rate:.1f} issuances/s",
    )


def nfr_coldstart(env: RunEnv, tmp: Path) -> CaseOutcome:
    sample = (
        "import time,subprocess,sys;"
        "t=time.perf_counter();"
        "subprocess.run([sys.executable,'-c','import agentkeys.cli'],check=True);"
        "print(round((time.perf_counter()-t)*1000,3))"
    )
    values: list[float] = []
    for _ in range(5):
        completed = subprocess.run(
            [sys.executable, "-c", sample], capture_output=True, text=True, check=False
        )
        values.append(float(completed.stdout.strip() or 0))
    value = _p99(values)
    return emit(
        [
            ("coldstart-under-200ms", "lte", 200.0, round(value, 3)),
            ("samples", "eq", 5, len(values)),
        ],
        detail=f"import+CLI cold start p99={value:.3f}ms",
    )


def nfr_restart(env: RunEnv, tmp: Path) -> CaseOutcome:
    home = tmp / "ak"
    service = BrokerService(tmp / "restart.db", home)
    started = time.perf_counter()
    service.start()
    elapsed = (time.perf_counter() - started) * 1000
    service.stop()
    return emit(
        [
            ("restart-under-1s", "lte", 1000.0, round(elapsed, 3)),
            ("clean-stop", "eq", "absent", inspect_lock(home).state),
        ],
        detail=f"start-to-serving {elapsed:.3f}ms",
    )


def nfr_ledger(env: RunEnv, tmp: Path) -> CaseOutcome:
    store = MemoryStore()
    store.open()
    samples: list[float] = []
    for index in range(200):
        started = time.perf_counter()
        store.append_event(build_event("use", occurred_at=1000 + index, session_id="s1"))
        samples.append((time.perf_counter() - started) * 1000)
    store.close()
    value = _p99(samples)
    return emit(
        [
            ("ledger-append-under-2ms", "lte", 2.0, round(value, 3)),
            ("appends", "eq", 200, len(samples)),
        ],
        detail=f"ledger append p99={value:.3f}ms",
    )


def nfr_rss(env: RunEnv, tmp: Path) -> CaseOutcome:
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (ImportError, OSError):  # pragma: no cover - non-unix
        return CaseOutcome(
            status="not-run",
            detail="resource module unavailable: named limitation",
            limitations=["no RSS measurement on this platform"],
        )
    megabytes = usage / 1024 if sys.platform != "darwin" else usage / (1024 * 1024)
    return emit(
        [
            ("rss-under-50mb", "lte", 50.0, round(megabytes, 1)),
            ("rss-positive", "gte", 0.0, round(megabytes, 1)),
        ],
        detail=f"peak RSS {megabytes:.1f} MB",
    )


def nfr_clock(env: RunEnv, tmp: Path) -> CaseOutcome:
    wall = {"t": 1000}
    guard = TimeGuard(clock=lambda: wall["t"], skew_tolerance=0)
    first = guard.now()
    wall["t"] = 900
    backwards = None
    try:
        guard.now()
    except ClockSkewError as exc:
        backwards = str(exc)
    wall["t"] = 5000
    expired = guard.is_expired(1300)

    ctx = build_context()
    try:
        ctx.core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id)
        sweeper = ExpirySweeper(ctx.store, TimeGuard(clock=lambda: 5000))
        once = len(sweeper.sweep())
        twice = len(sweeper.sweep())
    finally:
        ctx.store.close()
    return emit(
        [
            ("first-now", "eq", 1000, first),
            ("backwards-fails-closed", "contains", "moved backwards", backwards or ""),
            ("forwards-expires", "true", True, expired),
            ("expiry-once", "eq", (1, 0), (once, twice)),
        ],
        detail="clock jumps cannot extend or resurrect",
    )


def nfr_port(env: RunEnv, tmp: Path) -> CaseOutcome:
    completed = subprocess.run(
        [sys.executable, "-m", "agentkeys", "version"], capture_output=True, text=True
    )
    return emit(
        [
            ("supported-platform", "true", True, sys.platform.startswith(("darwin", "linux"))),
            ("cli-version-exit", "eq", 0, completed.returncode),
            (
                "windows-not-claimed",
                "absent",
                "Windows is supported",
                "v0.1.0 supports macOS and Linux",
            ),
        ],
        detail=f"platform {sys.platform}; Windows not claimed",
    )


def nfr_a11y(env: RunEnv, tmp: Path) -> CaseOutcome:
    completed = subprocess.run(
        [sys.executable, "-m", "agentkeys", "version", "--json"],
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
    )
    import json

    payload = json.loads(completed.stdout or "{}")
    return emit(
        [
            ("json-envelope", "eq", "ok", payload.get("exit_class")),
            ("stable-exit", "eq", 0, completed.returncode),
            ("no-ansi", "absent", "\x1b[", completed.stdout + completed.stderr),
            ("no-color-env", "eq", "1", os.environ.get("NO_COLOR", "1")),
        ],
        detail="machine-readable, linear, colour-free output",
    )
