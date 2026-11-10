"""The launch wrapper: `agentkeys run --server <ref>` under a protected boundary (M5, WBS 5.1)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from agentkeys.stdio.proxy import StdioProxy
from agentkeys.stdio.substitute import Substitution, build_virtualized_env

__all__ = ["LaunchPlan", "plan_launch", "run_under_broker"]

_VIRTUALIZED_MARKER = "AGENTKEYS_VIRTUALIZED"


@dataclass(frozen=True)
class LaunchPlan:
    """What will be spawned, and what was virtualized (no secret material)."""

    argv: tuple[str, ...]
    substitution: Substitution

    def child_env(self) -> Mapping[str, str]:
        env = dict(self.substitution.env)
        env[_VIRTUALIZED_MARKER] = "1"
        return env


def plan_launch(
    server_argv: Sequence[str],
    *,
    requested_env: Mapping[str, str],
    resolve: Callable[[str, str], str],
    session_id: str = "stdio",
) -> LaunchPlan:
    """Build the child environment for a stdio server: references in, scoped tokens substituted."""
    if not server_argv:
        raise ValueError("a server command is required")
    substitution = build_virtualized_env(requested_env, resolve=resolve, session_id=session_id)
    return LaunchPlan(argv=tuple(server_argv), substitution=substitution)


def run_under_broker(
    plan: LaunchPlan,
    *,
    stdin: object | None = None,
    stdout: object | None = None,
    log: Callable[[str], None] | None = None,
) -> int:
    """Spawn the child with the virtualized environment and proxy its stdio."""
    proxy = StdioProxy(plan.argv, env=plan.child_env(), log=log)
    return proxy.run(stdin=stdin, stdout=stdout)  # type: ignore[arg-type]
