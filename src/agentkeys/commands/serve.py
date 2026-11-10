"""`agentkeys serve` — the long-lived user-scoped broker process (M12, WBS 12.1)."""

from __future__ import annotations

import argparse
import json
import sys

from agentkeys.config import Config, ConfigError, agentkeys_home, load_config
from agentkeys.exit_codes import ExitCode, json_envelope
from agentkeys.ops import BrokerService
from agentkeys.service import write_user_units

__all__ = ["run_serve"]


def run_serve(args: argparse.Namespace) -> int:
    """Start the broker (foreground) or write the user units with `--write-units`."""
    as_json = bool(getattr(args, "json", False))
    try:
        config: Config = load_config(getattr(args, "config", None))
    except ConfigError as exc:
        print(f"agentkeys serve: denied: {exc}", file=sys.stderr)
        return int(ExitCode.DENIED)

    home = agentkeys_home()
    if getattr(args, "write_units", False):
        paths = write_user_units(home / "units", home=home)
        if as_json:
            print(json.dumps(json_envelope(ExitCode.OK, data={"units": [str(p) for p in paths]})))
        else:
            for path in paths:
                print(path)
        return int(ExitCode.OK)

    service = BrokerService(config.store_path, home)
    try:
        service.start()
    except RuntimeError as exc:
        print(f"agentkeys serve: denied: {exc}", file=sys.stderr)
        return int(ExitCode.DENIED)
    if as_json:
        print(json.dumps(json_envelope(ExitCode.OK, data={"pid": __import__("os").getpid()})))
    service.wait()
    return int(ExitCode.OK)
