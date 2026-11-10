"""The case registry: cases.yaml metadata plus one executor per case id."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from agentkeys.fieldtest import packs_attack, packs_core, packs_docker, packs_ops
from agentkeys.fieldtest.cases import CASES_PATH, load_cases
from agentkeys.fieldtest.models import Case, Executor

__all__ = ["EXECUTORS", "CasesError", "load_registry", "packs", "registered_ids"]


class CasesError(Exception):
    """The registry and cases.yaml disagree (a case without metadata or without an executor)."""


EXECUTORS: dict[str, Executor] = {
    # Docker
    "FT-DK-IMAGE": packs_docker.dk_image,
    "FT-DK-COMPOSE": packs_docker.dk_compose,
    "FT-DK-QUICKSTART": packs_docker.dk_quickstart,
    "FT-DK-BOUNDARY": packs_docker.dk_boundary,
    "FT-DK-AIRGAP": packs_docker.dk_airgap,
    "FT-DK-EVIDENCE": packs_docker.dk_evidence,
    "FT-DK-SINGLEWRITER": packs_docker.dk_singlewriter,
    # Core
    "FT-CL-FIRST": packs_core.cl_first,
    "FT-CL-ENV": packs_core.cl_env,
    "FT-CL-HEADER": packs_core.cl_header,
    "FT-CL-EXCHANGE": packs_core.cl_exchange,
    "FT-CL-TTL": packs_core.cl_ttl,
    "FT-CL-ROTATE": packs_core.cl_rotate,
    "FT-CL-TWOHARNESS": packs_core.cl_two_harnesses,
    # Binding
    "FT-BR-AUDIENCE": packs_core.br_audience,
    "FT-BR-TOOL": packs_core.br_tool,
    "FT-BR-SESSION": packs_core.br_session,
    "FT-BR-STALE": packs_core.br_stale,
    # stdio
    "FT-ST-NOSECRET": packs_core.stdio_nosecret,
    "FT-ST-NOPASSTHRU": packs_core.stdio_nopassthrough,
    # Evasion
    "FT-EV-DOTENV": packs_core.ev_dotenv,
    "FT-EV-CLOUD": packs_core.ev_cloud,
    "FT-EV-KEYCHAIN": packs_core.ev_keychain,
    "FT-EV-ENFORCE": packs_core.ev_enforce,
    # Fail-closed
    "FT-FC-LOCKED": packs_core.fc_locked,
    "FT-FC-ABSENT": packs_core.fc_absent,
    "FT-FC-CONFIG": packs_core.fc_config,
    "FT-FC-STORE": packs_core.fc_store,
    "FT-FC-SINK": packs_core.fc_sink,
    "FT-FC-CRASH": packs_core.fc_crash,
    # Revocation
    "FT-RK-KILLTIME": packs_core.rk_killtime,
    "FT-RK-SCOPE": packs_core.rk_scope,
    "FT-RK-INFLIGHT": packs_core.rk_inflight,
    "FT-RK-UNKNOWN": packs_core.rk_unknown,
    "FT-RK-ATTR": packs_core.rk_attr,
    # Audit
    "FT-LA-EXPORT": packs_core.la_export,
    "FT-LA-TAMPER": packs_core.la_tamper,
    "FT-LA-NOSECRET": packs_core.la_nosecret,
    "FT-LA-EVENT": packs_core.la_event,
    # Step-up
    "FT-SU-APPROVED": packs_core.su_approved,
    "FT-SU-DENIED": packs_core.su_denied,
    # Harness
    "FT-HC-CLAUDE": packs_attack.hc_claude,
    "FT-HC-CURSOR": packs_attack.hc_cursor,
    "FT-HC-GENERIC": packs_attack.hc_generic,
    "FT-HC-NOTYET": packs_attack.hc_notyet,
    # Air-gap
    "FT-AG-OFFLINE": packs_attack.ag_offline,
    # Attack
    "FT-AP-CONTEXTDUMP": packs_attack.ap_contextdump,
    "FT-AP-TAMPER": packs_attack.ap_tamper,
    "FT-AP-WIDEN": packs_attack.ap_widen,
    "FT-AP-EVIDENCE": packs_attack.ap_evidence,
    "FT-AP-FLOOD": packs_attack.ap_flood,
    # Migration
    "FT-MP-SCANMIGRATE": packs_attack.mp_scan_migrate,
    # Ops
    "FT-OPS-SERVE": packs_ops.ops_serve,
    "FT-OPS-BACKUP": packs_ops.ops_backup,
    "FT-OPS-RESTORE": packs_ops.ops_restore,
    "FT-OPS-MIGRATE": packs_ops.ops_migrate,
    "FT-OPS-DOCTOR": packs_ops.ops_doctor,
    "FT-OPS-DRILL": packs_ops.ops_drill,
    "FT-OPS-RETENTION": packs_ops.ops_retention,
    # NFR
    "FT-NFR-INJECT": packs_ops.nfr_inject,
    "FT-NFR-BACKEND": packs_ops.nfr_backend,
    "FT-NFR-THROUGHPUT": packs_ops.nfr_throughput,
    "FT-NFR-COLDSTART": packs_ops.nfr_coldstart,
    "FT-NFR-RESTART": packs_ops.nfr_restart,
    "FT-NFR-LEDGER": packs_ops.nfr_ledger,
    "FT-NFR-RSS": packs_ops.nfr_rss,
    "FT-NFR-CLOCK": packs_ops.nfr_clock,
    "FT-NFR-PORT": packs_ops.nfr_port,
    "FT-NFR-A11Y": packs_ops.nfr_a11y,
    # Conformance / honesty
    "FT-CONF-STANDARDS": packs_attack.conf_standards,
    "FT-CONF-BACKENDS": packs_attack.conf_backends,
    "FT-SC-INREPO": packs_attack.conf_supply,
    "FT-HONESTY-GAPS": packs_attack.conf_gaps,
    "FT-HONESTY-REPORT": packs_attack.conf_report,
}


def load_registry(path: str | Path | None = None) -> tuple[Case, ...]:
    """Load the frozen cases and refuse any mismatch with the executor registry."""
    cases = load_cases(path or CASES_PATH)
    ids = {case.id for case in cases}
    missing_executor = sorted(ids - set(EXECUTORS))
    missing_metadata = sorted(set(EXECUTORS) - ids)
    if missing_executor or missing_metadata:
        raise CasesError(
            f"registry mismatch: no executor for {missing_executor}; "
            f"no cases.yaml entry for {missing_metadata}"
        )
    if len(ids) != len(cases):
        raise CasesError("duplicate case ids in cases.yaml")
    return cases


def registered_ids() -> tuple[str, ...]:
    return tuple(sorted(EXECUTORS))


def packs() -> Mapping[str, tuple[Case, ...]]:
    grouped: dict[str, list[Case]] = {}
    for case in load_registry():
        grouped.setdefault(case.pack, []).append(case)
    return {pack: tuple(items) for pack, items in grouped.items()}
