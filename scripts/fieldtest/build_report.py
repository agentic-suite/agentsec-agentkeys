#!/usr/bin/env python3
"""Write the generated draft next to the hand-maintained report (never over it)."""

from __future__ import annotations

import sys

from agentkeys.fieldtest.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["build-report", *sys.argv[1:]]))
