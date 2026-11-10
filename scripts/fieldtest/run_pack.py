#!/usr/bin/env python3
"""Run field-test packs. Thin wrapper over `python -m agentkeys.fieldtest run`."""

from __future__ import annotations

import sys

from agentkeys.fieldtest.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["run", *sys.argv[1:]]))
