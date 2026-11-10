"""User-scoped service units for `agentkeys serve` (M12, WBS 12.1).

Both units run in the user's session: launchd `LaunchAgents` and a systemd **user** unit. Neither
asks for root; the unit only invokes `agentkeys serve` with the user's `AGENTKEYS_HOME`.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

__all__ = ["launchd_plist", "systemd_unit", "write_user_units"]

_LABEL = "dev.agentkeys.broker"


def _executable(executable: str | None) -> str:
    return executable or shutil.which("agentkeys") or "agentkeys"


def launchd_plist(executable: str | None, home: str | Path) -> str:
    """A LaunchAgents plist: RunAtLoad, KeepAlive, user HOME, no root."""
    program = _executable(executable)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{_LABEL}</string>
  <key>ProgramArguments</key>
  <array><string>{program}</string><string>serve</string></array>
  <key>EnvironmentVariables</key>
  <dict><key>AGENTKEYS_HOME</key><string>{home}</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Background</string>
</dict>
</plist>
"""


def systemd_unit(executable: str | None, home: str | Path) -> str:
    """A systemd **user** unit (no User=, no root)."""
    program = _executable(executable)
    return f"""[Unit]
Description=agentkeys credential broker (user)
After=default.target

[Service]
Type=simple
Environment=AGENTKEYS_HOME={home}
ExecStart={program} serve
Restart=on-failure
RestartSec=2
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=default.target
"""


def write_user_units(
    directory: str | Path, *, executable: str | None = None, home: str | Path
) -> tuple[Path, ...]:
    """Write both unit files (`0600`) and return their paths."""
    base = Path(directory)
    base.mkdir(parents=True, exist_ok=True)
    files = {
        "agentkeys.launchd.plist": launchd_plist(executable, home),
        "agentkeys.service": systemd_unit(executable, home),
    }
    paths: list[Path] = []
    for name, text in files.items():
        path = base / name
        path.write_text(text, encoding="utf-8")
        os.chmod(path, 0o600)
        paths.append(path)
    return tuple(paths)
