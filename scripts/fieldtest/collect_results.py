#!/usr/bin/env python3
"""Aggregate committed verdicts per pack and overall."""

from __future__ import annotations

import sys

from agentkeys.fieldtest.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["collect", *sys.argv[1:]]))
