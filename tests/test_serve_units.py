"""12.1 — serve lifecycle, lock honesty, and user-scoped units (no root)."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from agentkeys.ops import BrokerService, inspect_lock, lock_path
from agentkeys.service import launchd_plist, systemd_unit, write_user_units


def test_start_publishes_a_live_lock_and_stop_removes_it(tmp_path: Path) -> None:
    home = tmp_path / "ak"
    service = BrokerService(tmp_path / "store.db", home)
    service.start()
    try:
        state = inspect_lock(home)
        assert state.state == "live"
        assert state.pid == os.getpid()
        assert lock_path(home).stat().st_mode & 0o777 == 0o600
        with pytest.raises(RuntimeError, match="already running"):
            BrokerService(tmp_path / "store.db", home).start()
    finally:
        service.stop()
    assert inspect_lock(home).state == "absent"


def test_a_stale_lock_is_replaced(tmp_path: Path) -> None:
    home = tmp_path / "ak"
    home.mkdir(mode=0o700)
    lock_path(home).write_text(json.dumps({"pid": 999_999_999}), encoding="utf-8")
    assert inspect_lock(home).state == "stale"
    service = BrokerService(tmp_path / "store.db", home)
    service.start()
    try:
        assert inspect_lock(home).state == "live"
    finally:
        service.stop()


def test_an_unreadable_lock_is_stale(tmp_path: Path) -> None:
    home = tmp_path / "ak"
    home.mkdir(mode=0o700)
    lock_path(home).write_text("not json", encoding="utf-8")
    assert inspect_lock(home).state == "stale"


def test_sigterm_closes_cleanly_and_removes_the_lock(tmp_path: Path) -> None:
    home = tmp_path / "ak"
    script = (
        "from agentkeys.ops import BrokerService\n"
        "import sys\n"
        "service = BrokerService(sys.argv[1], sys.argv[2])\n"
        "service.start()\n"
        "print('ready', flush=True)\n"
        "service.wait()\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(tmp_path / "store.db"), str(home)],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "ready"
        assert inspect_lock(home).state == "live"
        process.send_signal(signal.SIGTERM)
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:  # pragma: no cover - safety net
            process.kill()
    assert not lock_path(home).exists()


def test_launchd_unit_is_user_scoped(tmp_path: Path) -> None:
    text = launchd_plist("/usr/local/bin/agentkeys", tmp_path)
    assert "dev.agentkeys.broker" in text
    assert "<string>serve</string>" in text
    assert "root" not in text


def test_systemd_unit_is_a_user_unit(tmp_path: Path) -> None:
    text = systemd_unit("/usr/local/bin/agentkeys", tmp_path)
    assert "ExecStart=/usr/local/bin/agentkeys serve" in text
    assert "User=" not in text
    assert "WantedBy=default.target" in text
    assert "NoNewPrivileges=yes" in text


def test_units_are_written_0600(tmp_path: Path) -> None:
    paths = write_user_units(tmp_path / "units", executable="/bin/agentkeys", home=tmp_path)
    assert len(paths) == 2
    for path in paths:
        assert path.stat().st_mode & 0o777 == 0o600
