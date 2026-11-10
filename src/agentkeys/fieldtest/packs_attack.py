"""Executors for harness, air-gap, attack, migration, and conformance field cases."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from unittest import mock

from agentkeys.backends.contract import BackendError
from agentkeys.conformance import run_conformance
from agentkeys.contracts.registry import UnknownReference
from agentkeys.egress.contract import (
    AudienceMismatch,
    InjectionRequest,
    WideningRefused,
)
from agentkeys.egress.env import DEFAULT_VARIABLE
from agentkeys.egress.header import HeaderInjector
from agentkeys.events import build_event
from agentkeys.evidence import scan_evidence, scan_text
from agentkeys.export import render_rows
from agentkeys.fieldtest.models import Assertion, CaseOutcome, RunEnv, emit
from agentkeys.invariants import AUDIENCE, TOOL, build_context
from agentkeys.ledger import verify_chain
from agentkeys.migrate import FileSecretWriter, Migrator
from agentkeys.recipes import (
    RECIPES,
    RecipeError,
    get_recipe,
    render_mcp_wiring,
    run_recipe_smoke,
    support_label,
    validate_wiring,
)
from agentkeys.revoke import Revoker
from agentkeys.store.memory import MemoryStore
from agentkeys.tamper import ConfigIntegrity, TamperError, TamperGuard

_PLANTED_VALUE = "ghp_FAKE0000000000000000000000000000000000"
_SEEDED = "sk-FAKE000000000000000000000000000000000000"


def _warn(detail: str, limitation: str, assertions: Sequence[Any]) -> CaseOutcome:
    return CaseOutcome(
        status="warn", detail=detail, assertions=list(assertions), limitations=[limitation]
    )


def _recipe_case(name: str) -> tuple[Any, dict[str, Any], Any]:
    recipe = get_recipe(name)
    wiring = render_mcp_wiring(recipe, reference="akref:file/agentkeys/dev/token")
    validate_wiring(recipe, wiring)
    ctx = build_context()
    try:
        resolved = ctx.core.resolve(
            "ref_1", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id
        )
        expected = resolved.token or ""
        if recipe.egress_kind == "header":

            def target(injection: Any) -> bool:
                return (injection.headers or {}).get("Authorization") == f"Bearer {expected}"
        else:

            def target(injection: Any) -> bool:
                return (injection.env or {}).get(DEFAULT_VARIABLE) == expected

        smoke = run_recipe_smoke(
            recipe,
            ctx.core,
            session_id=ctx.session_id,
            reference_id="ref_1",
            audience=AUDIENCE,
            tool=TOOL,
            target=target,
        )
    finally:
        ctx.store.close()
    return recipe, wiring, smoke


def _recipe_assertions(
    recipe: Any, wiring: dict[str, Any], smoke: Any
) -> list[tuple[str, str, object, object]]:
    return [
        ("wiring-valid", "true", True, recipe.supported),
        ("wiring-command-is-broker", "contains", "agentkeys", str(wiring)),
        ("smoke-authenticated", "true", True, smoke.ok),
        ("transcript-only-reference", "eq", ("ref_1",), smoke.transcript),
    ]


def hc_claude(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-35: Claude Code recipe — wiring + smoke + a live headless `claude -p` run."""
    recipe, wiring, smoke = _recipe_case("claude-code")
    assertions = _recipe_assertions(recipe, wiring, smoke)
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        return _warn(
            "Claude Code: wiring + smoke green; claude CLI absent",
            "claude CLI not installed on this box; wiring + smoke verified, "
            "the live run is declared (plan §8)",
            [Assertion(*a) for a in assertions],
        )
    version = subprocess.run(
        [claude_bin, "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()
    mcp_config = tmp / "mcp.json"
    mcp_config.write_text(json.dumps(wiring, indent=2))
    live = subprocess.run(
        [claude_bin, "--mcp-config", str(mcp_config), "-p", "list tools"],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        cwd=str(tmp),
    )
    live_output = (live.stdout + live.stderr).strip()
    assertions += [
        ("claude-installed", "contains", "Claude Code", version),
        (
            "live-no-secret",
            "eq",
            (),
            scan_text(live_output),
        ),
    ]
    if live.returncode != 0 or "Not logged in" in live_output:
        # The honest state: the CLI is installed but not authenticated for
        # headless use. The wiring + smoke are green; the live loop is declared,
        # not faked.
        return _warn(
            f"Claude Code {version}: wiring + smoke green; live headless run not authenticated",
            "claude CLI installed but not logged in on this box "
            f"({live_output[:80] or 'exit ' + str(live.returncode)}); "
            "wiring + smoke verified, the live run is declared (plan §8)",
            [Assertion(*a) for a in assertions],
        )
    assertions += [("live-exit-zero", "true", True, live.returncode == 0)]
    return emit(
        list(assertions),
        detail=f"Claude Code {version}: wiring + smoke + live headless run green",
    )


def hc_cursor(env: RunEnv, tmp: Path) -> CaseOutcome:
    """SC-36: Cursor recipe — wiring + smoke; Cursor is a GUI IDE with no headless CLI."""
    recipe, wiring, smoke = _recipe_case("cursor")
    assertions = _recipe_assertions(recipe, wiring, smoke)
    cursor_bin = shutil.which("cursor") or shutil.which("cursor-agent")
    if cursor_bin is None:
        return _warn(
            "Cursor: wiring + smoke green; no headless CLI on this box",
            "Cursor is a GUI IDE (VS Code fork) with no headless/evidence-capturing "
            "CLI surface on this box; the wiring + smoke are verified and the live "
            "run is declared (plan §8)",
            [Assertion(*a) for a in assertions],
        )
    version = subprocess.run(
        [cursor_bin, "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()
    return emit(
        [*assertions, ("cursor-version", "present", True, version)],
        detail=f"Cursor {version}: wiring + smoke green",
    )


def hc_generic(env: RunEnv, tmp: Path) -> CaseOutcome:
    from agentkeys.sdk import Broker

    ctx = build_context()
    broker = Broker(ctx.core)
    try:
        resolved = broker.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id)
        used = broker.use(resolved.issuance.issuance_id, resolved.token or "", now=1001)
    finally:
        ctx.store.close()
    return emit(
        [
            ("resolved", "present", True, resolved.token),
            ("consumed", "eq", "consumed", used.status),
            ("no-secret-read-out", "true", True, not hasattr(broker, "get_secret")),
        ],
        detail="public SDK contract: resolve → use, no get_secret",
    )


def hc_notyet(env: RunEnv, tmp: Path) -> CaseOutcome:
    label = support_label(RECIPES["jetbrains"])
    refused = None
    try:
        validate_wiring(RECIPES["jetbrains"], render_mcp_wiring(RECIPES["jetbrains"]))
    except RecipeError as exc:
        refused = str(exc)
    return emit(
        [
            ("labelled-not-yet", "contains", "not yet", label),
            ("wiring-refused", "contains", "not yet", refused or ""),
            ("never-supported", "absent", "supported", label),
        ],
        detail="uncovered harness is labelled not-yet",
    )


def ag_offline(env: RunEnv, tmp: Path) -> CaseOutcome:
    def no_socket(*args: Any, **kwargs: Any) -> Any:
        raise OSError("network disabled")

    with (
        mock.patch.object(socket, "socket", no_socket),
        mock.patch.object(socket, "create_connection", no_socket),
    ):
        ctx = build_context()
        try:
            resolved = ctx.core.resolve(
                "ref_1", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id
            )
            used = ctx.core.use(resolved.issuance.issuance_id, resolved.token or "", now=1001)
            Revoker(ctx.store, clock=lambda: 1000).revoke(
                "session", ctx.session_id, reason="offline", requested_by="op"
            )
            session = ctx.store.get_session(ctx.session_id)
        finally:
            ctx.store.close()
        from agentkeys.store.contract import DriverNotFound
        from agentkeys.store.loader import load_driver

        refused = None
        try:
            load_driver("vault")
        except DriverNotFound as exc:
            refused = str(exc)
    return emit(
        [
            ("resolved-offline", "present", True, resolved.token),
            ("used-offline", "eq", "consumed", used.status),
            ("revoked-offline", "eq", 1, session.revoke_epoch if session else None),
            ("cloud-backend-refused", "contains", "vault", refused or ""),
        ],
        detail="core + revoke work with sockets disabled; unknown backend refuses",
    )


def ap_contextdump(env: RunEnv, tmp: Path) -> CaseOutcome:
    ctx = build_context()
    try:
        resolved = ctx.core.resolve(
            "ref_1", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id
        )
        dump = (
            render_rows(ctx.store.read_ledger())
            + str([doc.to_dict() for doc in ctx.core.list_references()])
            + str(resolved.issuance.to_dict())
            + "transcript: ref_1"
        )
    finally:
        ctx.store.close()
    seeded = scan_text(_SEEDED)
    return emit(
        [
            ("no-token-in-dump", "true", True, (resolved.token or "") not in dump),
            ("no-secret-shapes", "eq", (), scan_text(dump)),
            ("references-present", "contains", "ref_1", dump),
            ("control-fires", "gte", 1, len(seeded)),
        ],
        detail="dump holds references only; the seeded control is caught",
    )


def ap_tamper(env: RunEnv, tmp: Path) -> CaseOutcome:
    config = tmp / "config.toml"
    config.write_text('enforce_mode = "enforce"\n')
    integrity = ConfigIntegrity(config)
    integrity.pin()
    config.write_text('enforce_mode = "monitor"\n')
    store = MemoryStore()
    store.open()
    guard = TamperGuard(store, integrity, clock=lambda: 1000)
    tampered = None
    try:
        guard.check(session_id="s1")
    except TamperError as exc:
        tampered = str(exc)
    store.append_event(
        build_event("issuance.created", occurred_at=1000, session_id="s1")
    )
    rows = list(store.read_ledger())
    rows[0] = rows[0].__class__(
        seq=rows[0].seq,
        event=rows[0].event.__class__(**{**rows[0].event.__dict__, "reason": "rewritten"}),
        prev_hash=rows[0].prev_hash,
        hash=rows[0].hash,
    )
    chain = verify_chain(tuple(rows))
    store.close()
    ctx = build_context()
    try:
        spoof = None
        try:
            ctx.core.resolve(
                "ref_invented", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id
            )
        except UnknownReference as exc:
            spoof = str(exc)
    finally:
        ctx.store.close()
    return emit(
        [
            ("config-tamper", "contains", "config-tampered", tampered or ""),
            ("ledger-tamper", "true", True, chain.intact is False),
            ("spoof-refused", "contains", "ref_invented", spoof or ""),
        ],
        detail="config, ledger, and spoof tamper all fail closed",
    )


def ap_widen(env: RunEnv, tmp: Path) -> CaseOutcome:
    ctx = build_context()
    try:
        resolved = ctx.core.resolve(
            "ref_1", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id
        )
    finally:
        ctx.store.close()
    injector = HeaderInjector(AUDIENCE)
    tool = scope = audience = False
    try:
        injector.apply(resolved, request=InjectionRequest(audience=AUDIENCE, tool="other"))
    except WideningRefused:
        tool = True
    try:
        injector.apply(
            resolved, request=InjectionRequest(audience=AUDIENCE, tool=TOOL, scope="admin")
        )
    except WideningRefused:
        scope = True
    try:
        injector.apply(
            resolved, request=InjectionRequest(audience="https://other.example", tool=TOOL)
        )
    except AudienceMismatch:
        audience = True
    return emit(
        [
            ("tool", "true", True, tool),
            ("scope", "true", True, scope),
            ("audience", "true", True, audience),
        ],
        detail="all widening vectors refused",
    )


def ap_evidence(env: RunEnv, tmp: Path) -> CaseOutcome:
    ctx = build_context()
    try:
        ctx.core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id)
        clean = scan_evidence(ctx.store)
        ctx.store.append_event(
            build_event(
                "exchange-rejected",
                occurred_at=2000,
                session_id=ctx.session_id,
                reason=_SEEDED,
            )
        )
        seeded = scan_evidence(ctx.store)
    finally:
        ctx.store.close()
    return emit(
        [
            ("clean-ok", "true", True, clean.ok),
            ("clean-rows", "gte", 2, clean.rows),
            ("seeded-fails", "true", True, seeded.ok is False),
            (
                "seeded-location",
                "contains",
                "ledger:",
                seeded.findings[0].location if seeded.findings else "",
            ),
        ],
        detail="evidence scanner is clean and its seeded control fires",
    )


def ap_flood(env: RunEnv, tmp: Path) -> CaseOutcome:
    ctx = build_context()
    try:
        ids = {
            ctx.core.resolve(
                "ref_1", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id
            ).issuance.issuance_id
            for _ in range(200)
        }
        created = [
            row for row in ctx.store.read_ledger() if row.event.event_name == "issuance.created"
        ]
        probes = 0
        for _ in range(5):
            try:
                ctx.core.resolve(
                    "ref_ghost", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id
                )
            except UnknownReference:
                probes += 1
    finally:
        ctx.store.close()
    return emit(
        [
            ("exactly-once-under-flood", "eq", 1, len(ids)),
            ("one-issuance-row", "eq", 1, len(created)),
            ("probes-still-refused", "eq", 5, probes),
        ],
        detail="flood is exactly-once; no bypass under load",
    )


def mp_scan_migrate(env: RunEnv, tmp: Path) -> CaseOutcome:
    from agentkeys.scan import scan

    source = env.repo_root / "tests" / "fixtures" / "scan_repo"
    repo = tmp / "repo"
    shutil.copytree(source, repo)
    before = scan(repo)
    planted = {(finding.path, finding.line) for finding in before.findings}
    store = MemoryStore()
    store.open()
    writer = FileSecretWriter(tmp / "creds.json")
    result = Migrator(store, writer).migrate(repo, repo / ".env", name="GITHUB_TOKEN")
    after = scan(repo)
    remaining = {(finding.path, finding.line) for finding in after.findings}
    output_blob = str(result.to_dict()) + before.to_dict().__str__() + after.to_dict().__str__()
    store.close()
    return emit(
        [
            ("recall", "gte", 7, len(planted)),
            (
                "value-gone-from-file",
                "true",
                True,
                _PLANTED_VALUE not in (repo / ".env").read_text(),
            ),
            (
                "value-in-backend",
                "true",
                True,
                writer.read(result.reference.path) == _PLANTED_VALUE,
            ),
            ("finding-closed", "true", True, (".env", 2) not in remaining),
            ("zero-printed", "true", True, _PLANTED_VALUE not in output_blob),
            ("broad-reuse-flagged", "gte", 1, before.broad_reuse),
        ],
        detail="100% recall, 0 printed, finding closed, broad reuse flagged",
    )


def conf_standards(env: RunEnv, tmp: Path) -> CaseOutcome:
    results = run_conformance()
    failed = [result.suite for result in results if result.status == "fail"]
    unsupported = [result.suite for result in results if result.status == "not-supported"]
    return emit(
        [
            ("no-failures", "eq", [], failed),
            ("dpop-not-supported", "eq", ["rfc9449"], unsupported),
            ("has-passing-suites", "gte", 9, len([r for r in results if r.status == "pass"])),
        ],
        detail="conformance green; DPoP explicitly not supported",
    )


def conf_backends(env: RunEnv, tmp: Path) -> CaseOutcome:
    from agentkeys.backends.contract import admit_backend

    class Broken:
        backend_id = "broken"

    refused = None
    try:
        admit_backend("broken", Broken())
    except BackendError as exc:
        refused = str(exc)
    results = {r.suite: r for r in run_conformance(["backends"])}
    return emit(
        [
            ("backends-pass", "eq", "pass", results["backends"].status),
            ("broken-refused", "contains", "not conformant", refused or ""),
        ],
        detail="drivers admitted only through conformance",
    )


def conf_supply(env: RunEnv, tmp: Path) -> CaseOutcome:
    from agentkeys.supplychain import build_sbom, run_supply_checks

    checks = run_supply_checks(env.repo_root)
    failed = [check.id for check in checks if not check.ok]
    bom = build_sbom()
    return emit(
        [
            ("checks-pass", "eq", [], failed),
            ("sbom-format", "eq", "CycloneDX", bom.get("bomFormat")),
            ("security-txt", "true", True, (env.repo_root / "security.txt").is_file()),
        ],
        detail="stdlib-only, security.txt, CI gate, SBOM, fuzz targets",
    )


def conf_gaps(env: RunEnv, tmp: Path) -> CaseOutcome:
    doc = env.repo_root / "docs" / "explanation" / "honest-gaps.md"
    text = doc.read_text() if doc.is_file() else ""
    return emit(
        [
            ("gaps-doc", "true", True, doc.is_file()),
            ("gaps-named", "contains", "Not implemented", text),
            ("no-unsupported-claim", "absent", "fully supported", text.lower()),
            ("jetbrains-not-yet", "contains", "not yet", support_label(RECIPES["jetbrains"])),
        ],
        detail="claims stay at their evidence label; gaps are named",
    )


def conf_report(env: RunEnv, tmp: Path) -> CaseOutcome:
    from agentkeys.fieldtest.guards import REFUSED_MARKER, marker_present

    report = env.repo_root / "docs" / "field-test" / "v0.1.0" / "FIELD_TEST_REPORT.md"
    guard_test = env.repo_root / "tests" / "test_field_report_guard.py"
    return emit(
        [
            ("marker-present", "true", True, marker_present(report)),
            ("guard-test", "true", True, guard_test.is_file()),
            ("refusal-text", "eq", "HAND-MAINTAINED", REFUSED_MARKER),
        ],
        detail="the canonical report is hand-maintained and guarded",
    )
