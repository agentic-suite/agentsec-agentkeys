#!/usr/bin/env python3
"""Traceability gate: plan → case → result → report row."""

from __future__ import annotations

import sys

from agentkeys.fieldtest.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["trace", *sys.argv[1:]]))
