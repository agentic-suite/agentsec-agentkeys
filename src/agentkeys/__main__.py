"""`python -m agentkeys` entry point."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from agentkeys.cli import main


def run(argv: Sequence[str] | None = None) -> int:
    """Run the CLI (the `python -m agentkeys` path)."""
    return main(argv)


if __name__ == "__main__":  # pragma: no cover - the guard is exercised via `run`
    sys.exit(run())
