"""`agentkeys verify-log` — recompute the hash chain; never repair, never skip (M7, WBS 7.4)."""

from __future__ import annotations

import argparse
import json
import sys

from agentkeys.config import Config, ConfigError, load_config
from agentkeys.exit_codes import ExitCode, json_envelope
from agentkeys.ledger import ChainReport, verify_chain
from agentkeys.store.contract import DriverError, StoreError
from agentkeys.store.loader import load_driver

__all__ = ["run_verify_log"]


def _report_payload(report: ChainReport) -> dict[str, object]:
    return {
        "intact": report.intact,
        "rows": report.rows,
        "first_bad_seq": report.first_bad_seq,
        "gap_seqs": list(report.gap_seqs),
        "duplicate_seqs": list(report.duplicate_seqs),
        "reason": report.reason,
    }


def run_verify_log(args: argparse.Namespace) -> int:
    """Read-only chain verification; a broken chain is `TAMPER` with the bad `seq` named."""
    as_json = bool(getattr(args, "json", False))
    try:
        config: Config = load_config(getattr(args, "config", None))
        store = load_driver("sqlite", path=config.store_path, required=("durable",), enforce=True)
        store.open()
    except (ConfigError, DriverError, StoreError) as exc:
        if as_json:
            print(json.dumps(json_envelope(ExitCode.DENIED, reason=str(exc))))
        else:
            print(f"agentkeys verify-log: denied: {exc}", file=sys.stderr)
        return int(ExitCode.DENIED)

    try:
        report = verify_chain(store.read_ledger())
    finally:
        store.close()

    code = ExitCode.OK if report.intact else ExitCode.TAMPER
    if as_json:
        print(json.dumps(json_envelope(code, reason=report.reason, data=_report_payload(report))))
    elif report.intact:
        print(f"verify-log: intact ({report.rows} rows)")
    else:
        print(
            f"agentkeys verify-log: tamper detected at seq {report.first_bad_seq}: {report.reason}",
            file=sys.stderr,
        )
    return int(code)
