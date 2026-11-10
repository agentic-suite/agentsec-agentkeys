"""Executors for the Docker-topology field cases. They run only when Docker is available."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from agentkeys.evidence import scan_text
from agentkeys.fieldtest.models import CaseOutcome, RunEnv, emit

_COMPOSE = "field-test/v0.1.0/docker/compose.yaml"

_SINGLEWRITER = (
    "python - <<'PY'\n"
    "import os, pathlib\n"
    "home = pathlib.Path(os.environ.get('AGENTKEYS_HOME', '/data'))\n"
    "home.mkdir(parents=True, exist_ok=True)\n"
    "(home / 'config.toml').write_text(\n"
    '    \'enforce_mode = "enforce"\\nsink = ""\\n[store]\\npath = "%s"\\n\'\n'
    "    '[clock]\\nskew_tolerance = 30\\n[ttl.dev]\\nfloor = 30\\nceiling = 900\\n'\n"
    "    '[[backends]]\\nid = \"file\"\\nprecedence = 1\\n' % (home / 'probe.db')\n"
    ")\n"
    "PY\n"
    "agentkeys serve & sleep 2; agentkeys serve; test $? -ne 0"
)


def _available(env: RunEnv | None = None) -> bool:
    if env is not None and not env.docker:
        return False
    if shutil.which("docker") is None:
        return False
    probe = subprocess.run(["docker", "info"], capture_output=True, text=True, check=False)
    return probe.returncode == 0


def _not_run(reason: str) -> CaseOutcome:
    return CaseOutcome(status="not-run", detail=reason, limitations=[reason])


def _run(env: RunEnv, args: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, cwd=env.repo_root, capture_output=True, text=True, timeout=timeout, check=False
    )


def _compose(env: RunEnv, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(env, ["docker", "compose", "-f", _COMPOSE, *args])


def dk_image(env: RunEnv, tmp: Path) -> CaseOutcome:
    if not _available(env):
        return _not_run("docker unavailable: FT-DK-IMAGE requires the field topology (plan §3)")
    build = _compose(env, "build", "broker")
    inspect = _run(
        env,
        ["docker", "image", "inspect", "--format", "{{.Config.User}}", "agentkeys-fieldtest:local"],
    )
    user = inspect.stdout.strip()
    dockerfile = (env.repo_root / "field-test/v0.1.0/docker/Dockerfile.broker").read_text()
    return emit(
        [
            ("build-exit", "eq", 0, build.returncode),
            ("non-root-user", "true", True, bool(user) and user not in {"root", "0"}),
            ("no-secret-in-dockerfile", "eq", (), scan_text(dockerfile)),
        ],
        detail=f"image built; user={user or 'unset'}",
    )


def dk_compose(env: RunEnv, tmp: Path) -> CaseOutcome:
    if not _available(env):
        return _not_run("docker unavailable: FT-DK-COMPOSE requires the field topology")
    up = _compose(env, "up", "-d", "broker", "upstream")
    ps = _compose(env, "ps", "-q", "broker")
    try:
        running = bool(ps.stdout.strip())
    finally:
        _compose(env, "down")
    return emit(
        [("up-exit", "eq", 0, up.returncode), ("broker-running", "true", True, running)],
        detail="topology boots and reports healthy services",
    )


def dk_quickstart(env: RunEnv, tmp: Path) -> CaseOutcome:
    if not _available(env):
        return _not_run("docker unavailable: FT-DK-QUICKSTART requires the field topology")
    result = _compose(
        env,
        "run",
        "--rm",
        "broker",
        "python",
        "/work/scripts/fieldtest/run_pack.py",
        "--pack",
        "core",
        "--case",
        "FT-CL-ENV",
        "--results",
        "/results",
    )
    return emit(
        [
            ("container-run", "eq", 0, result.returncode),
            ("no-secret", "eq", (), scan_text(result.stdout + result.stderr)),
        ],
        detail="quickstart broker step runs inside the broker container",
    )


def dk_boundary(env: RunEnv, tmp: Path) -> CaseOutcome:
    if not _available(env):
        return _not_run("docker unavailable: FT-DK-BOUNDARY requires the field topology")
    probe = _compose(
        env,
        "run",
        "--rm",
        "--entrypoint",
        "sh",
        "child",
        "-c",
        "test ! -e /data && test ! -e /credentials && echo isolated",
    )
    return emit(
        [
            ("child-isolated", "eq", 0, probe.returncode),
            ("marks-isolated", "contains", "isolated", probe.stdout),
        ],
        detail="the child container has no path to the broker store or credentials",
    )


def dk_airgap(env: RunEnv, tmp: Path) -> CaseOutcome:
    """A `--network none` container: the offline pack passes with no network at all."""
    if not _available(env):
        return _not_run("docker unavailable: FT-DK-AIRGAP requires the field topology")
    # Named volumes mount root-owned; chown once (as root) so the 10001 broker user can write.
    _run(
        env,
        [
            "docker",
            "run",
            "--rm",
            "-v",
            "agentkeys-fieldtest_airgap-data:/data",
            "--user",
            "root",
            "--entrypoint",
            "sh",
            "agentkeys-fieldtest:local",
            "-c",
            "mkdir -p /data/results-airgap && chown -R 10001:10001 /data",
        ],
    )
    result = _run(
        env,
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "-v",
            f"{env.repo_root}:/work:ro",
            "-v",
            "agentkeys-fieldtest_airgap-data:/data",
            "-e",
            "AGENTKEYS_HOME=/data",
            "-e",
            "AGENTKEYS_FIELD_ROOT=/work",
            "-w",
            "/work",
            "--user",
            "10001:10001",
            "--entrypoint",
            "python",
            "agentkeys-fieldtest:local",
            "/work/scripts/fieldtest/run_pack.py",
            "--pack",
            "offline",
            "--case",
            "FT-AG-OFFLINE",
            "--results",
            "/data/results-airgap",
        ],
    )
    return emit(
        [
            ("airgap-run", "eq", 0, result.returncode),
            ("no-secret", "eq", (), scan_text(result.stdout + result.stderr)),
        ],
        detail="offline pack passes in a --network none container",
    )


def dk_evidence(env: RunEnv, tmp: Path) -> CaseOutcome:
    if not _available(env):
        return _not_run("docker unavailable: FT-DK-EVIDENCE requires the field topology")
    result = _compose(
        env, "run", "--rm", "scan", "python", "-m", "agentkeys.fieldtest", "scan", "--path", "/data"
    )
    return emit(
        [
            ("evidence-clean", "eq", 0, result.returncode),
            ("scan-ran", "contains", "scanned", result.stdout),
        ],
        detail="evidence scan over broker volumes is clean",
    )


def dk_singlewriter(env: RunEnv, tmp: Path) -> CaseOutcome:
    if not _available(env):
        return _not_run("docker unavailable: FT-DK-SINGLEWRITER requires the field topology")
    result = _compose(env, "run", "--rm", "broker", "sh", "-lc", _SINGLEWRITER)
    return emit(
        [
            ("second-writer-refused", "eq", 0, result.returncode),
            ("no-secret", "eq", (), scan_text(result.stdout + result.stderr)),
        ],
        detail="a second broker on the same home is refused",
    )
