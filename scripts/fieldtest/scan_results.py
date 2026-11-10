#!/usr/bin/env python3
"""Leak gate: scan every committed result for credential shapes (never print the value)."""

from __future__ import annotations

import sys

from agentkeys.fieldtest.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["scan", *sys.argv[1:]]))
