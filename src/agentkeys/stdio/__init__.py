"""stdio MCP credential virtualization: the flagship (M5)."""

from __future__ import annotations

from agentkeys.stdio.proxy import FrameTooLarge, StdioProxy, forward_frame
from agentkeys.stdio.substitute import (
    Substitution,
    SubstitutionError,
    build_virtualized_env,
    strip_client_credentials,
)

__all__ = [
    "FrameTooLarge",
    "StdioProxy",
    "Substitution",
    "SubstitutionError",
    "build_virtualized_env",
    "forward_frame",
    "strip_client_credentials",
]
