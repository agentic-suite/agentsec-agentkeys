"""`agentkeys doctor` — read-only health checks, each exit-coded (WBS 0.6, PRD 13 §6).

`doctor` never writes. It reports the effective configuration and names every failing check. Exit
precedence is `tamper (3) > denied (2) > ok (0)`.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentkeys import __version__
from agentkeys.config import Config, ConfigError, agentkeys_home, load_config
from agentkeys.exit_codes import ExitCode, json_envelope
from agentkeys.ledger import verify_chain
from agentkeys.ops import inspect_lock
from agentkeys.tamper import config_digest

__all__ = ["CURRENT_SCHEMA_VERSION", "Check", "check_platform", "doctor_exit", "run_doctor"]

#: The store schema version M0 understands (the full schema arrives in M1).
CURRENT_SCHEMA_VERSION = 1

_HOME_MODE = 0o700
_SUPPORTED_PLATFORMS = ("darwin", "linux")


@dataclass(frozen=True)
class Check:
    """One named doctor check and its outcome."""

    id: str
    status: str  # "ok" | "fail" | "skip"
    detail: str
    tamper: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "status": self.status, "detail": self.detail}


def check_platform(platform: str) -> Check:
    """macOS/Linux are supported; Windows is explicitly unsupported."""
    if platform.startswith(_SUPPORTED_PLATFORMS):
        return Check(id="platform", status="ok", detail=platform)
    reason = f"{platform} is not supported (v0.1.0 supports macOS and Linux only)"
    return Check(id="platform", status="fail", detail=reason)


def _check_config(
    config_path: str | Path | None, env: Mapping[str, str]
) -> tuple[Check, Config | None]:
    try:
        config = load_config(config_path, env=env)
    except ConfigError as exc:
        message = str(exc)
        tamper = "literal secret" in message
        return Check(id="config", status="fail", detail=message, tamper=tamper), None
    return Check(id="config", status="ok", detail=str(config.path)), config


def _check_home(home: Path) -> Check:
    if not home.exists():
        return Check(id="home", status="fail", detail=f"missing: {home}")
    if not home.is_dir():
        return Check(id="home", status="fail", detail=f"not a directory: {home}")
    mode = home.stat().st_mode & 0o777
    if mode != _HOME_MODE:
        return Check(
            id="home", status="fail", detail=f"permissions {mode:04o}, want {_HOME_MODE:04o}"
        )
    return Check(id="home", status="ok", detail=f"{home} (0700)")


def _check_store(config: Config | None) -> Check:
    if config is None:
        return Check(id="store", status="skip", detail="config invalid")
    store = config.store_path
    parent = store.parent
    if not parent.is_dir():
        return Check(id="store", status="fail", detail=f"store parent missing: {parent}")
    if not os.access(parent, os.W_OK):
        return Check(id="store", status="fail", detail=f"store parent not writable: {parent}")
    if not store.exists():
        return Check(id="store", status="ok", detail="schema_version: absent")
    try:
        connection = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
        try:
            row = connection.execute("SELECT version FROM schema_version").fetchone()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        return Check(id="store", status="fail", detail=f"unreadable store: {exc}", tamper=True)
    if row is None:
        return Check(id="store", status="fail", detail="schema_version: empty", tamper=True)
    version = int(row[0])
    if version > CURRENT_SCHEMA_VERSION:
        return Check(
            id="store",
            status="fail",
            detail=f"schema_version {version} is newer than supported {CURRENT_SCHEMA_VERSION}",
            tamper=True,
        )
    return Check(id="store", status="ok", detail=f"schema_version: {version}")


def _check_backends(config: Config | None) -> Check:
    if config is None:
        return Check(id="backends", status="skip", detail="config invalid")
    ids = ", ".join(backend.id for backend in config.backends)
    return Check(id="backends", status="ok", detail=f"{len(config.backends)} registered: {ids}")


def _check_clock(config: Config | None) -> Check:
    if config is None:
        return Check(id="clock", status="skip", detail="config invalid")
    first = time.time()
    second = time.time()
    if second < first:
        return Check(id="clock", status="fail", detail="wall clock moved backwards during check")
    return Check(id="clock", status="ok", detail=f"skew_tolerance={config.clock_skew_tolerance}s")


def _check_version() -> Check:
    return Check(id="version", status="ok", detail=__version__)


def _check_chain(config: Config | None) -> Check:
    """Recompute the ledger chain read-only; a break is tamper."""
    if config is None:
        return Check(id="chain", status="skip", detail="config invalid")
    if not config.store_path.exists():
        return Check(id="chain", status="ok", detail="no ledger yet")
    try:
        import sqlite3

        from agentkeys.store.sqlite import _ledger_row

        connection = sqlite3.connect(f"file:{config.store_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if "ledger" not in tables:
                return Check(id="chain", status="ok", detail="no ledger table yet")
            rows = tuple(
                _ledger_row(row) for row in connection.execute("SELECT * FROM ledger ORDER BY seq")
            )
        finally:
            connection.close()
    except sqlite3.Error as exc:
        return Check(id="chain", status="fail", detail=f"unreadable ledger: {exc}", tamper=True)
    report = verify_chain(rows)
    if not report.intact:
        return Check(
            id="chain",
            status="fail",
            detail=f"chain broken at seq {report.first_bad_seq}: {report.reason}",
            tamper=True,
        )
    return Check(id="chain", status="ok", detail=f"{report.rows} rows, chain intact")


def _check_lock(home: Path) -> Check:
    """A stale serve lock is a denial; a live lock is fine."""
    state = inspect_lock(home)
    if state.state == "stale":
        return Check(id="serve-lock", status="fail", detail=state.detail)
    return Check(id="serve-lock", status="ok", detail=state.detail)


def _check_config_integrity(config: Config | None) -> Check:
    """If a pinned digest exists, the config must still match it."""
    if config is None:
        return Check(id="config-integrity", status="skip", detail="config invalid")
    pinned = config.path.with_suffix(config.path.suffix + ".sha256")
    if not pinned.is_file():
        return Check(id="config-integrity", status="ok", detail="not pinned")
    expected = pinned.read_text(encoding="utf-8").strip()
    try:
        actual = config_digest(config.path)
    except OSError as exc:
        return Check(id="config-integrity", status="fail", detail=str(exc), tamper=True)
    if actual != expected:
        return Check(
            id="config-integrity", status="fail", detail="config digest mismatch", tamper=True
        )
    return Check(id="config-integrity", status="ok", detail="pinned digest matches")


def doctor_exit(checks: Sequence[Check]) -> int:
    """Map checks to the reserved exit code: tamper > denied > ok."""
    if any(check.status == "fail" and check.tamper for check in checks):
        return int(ExitCode.TAMPER)
    if any(check.status == "fail" for check in checks):
        return int(ExitCode.DENIED)
    return int(ExitCode.OK)


def _effective_config(config: Config | None) -> dict[str, Any] | None:
    if config is None:
        return None
    return {
        "path": str(config.path),
        "enforce_mode": config.enforce_mode,
        "sink": config.sink or "(local ledger only)",
        "store_path": str(config.store_path),
        "backends": [backend.id for backend in config.backends],
        "ttl": {
            name: {"floor": bound.floor, "ceiling": bound.ceiling}
            for name, bound in sorted(config.ttl.items())
        },
        "bindings": len(config.bindings),
    }


def run_doctor(
    *,
    config_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
    as_json: bool = False,
) -> int:
    """Run every check and report; read-only."""
    environ: Mapping[str, str] = os.environ if env is None else env
    checks: list[Check] = [check_platform(platform or sys.platform)]
    config_check, config = _check_config(config_path, environ)
    checks.append(config_check)
    checks.append(_check_home(agentkeys_home(environ)))
    checks.extend(
        [
            _check_store(config),
            _check_chain(config),
            _check_backends(config),
            _check_clock(config),
            _check_lock(agentkeys_home(environ)),
            _check_config_integrity(config),
            _check_version(),
        ]
    )

    code = ExitCode(doctor_exit(checks))
    failures = [check for check in checks if check.status == "fail"]
    if as_json:
        print(
            json.dumps(
                json_envelope(
                    code,
                    reason=failures[0].detail if failures else None,
                    data={
                        "checks": [check.as_dict() for check in checks],
                        "effective_config": _effective_config(config),
                    },
                )
            )
        )
        return int(code)

    for check in checks:
        print(f"[{check.status}] {check.id}: {check.detail}")
    effective = _effective_config(config)
    print("effective config:")
    if effective is None:
        print("  unavailable (config invalid)")
    else:
        for key, value in effective.items():
            print(f"  {key}: {value}")
    return int(code)
