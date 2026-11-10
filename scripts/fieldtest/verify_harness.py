#!/usr/bin/env python3
"""Prove the verifier: the gates must reject ungrounded, mismatched, and leaky results."""

from __future__ import annotations

import sys

from agentkeys.fieldtest.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["verify-harness"]))
