#!/usr/bin/env python3
"""Deep validation: re-derive every assertion from the committed results."""

from __future__ import annotations

import sys

from agentkeys.fieldtest.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["validate", *sys.argv[1:]]))
