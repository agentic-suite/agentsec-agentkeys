"""Harness recipes: the same broker wrapper below every harness (M10, WBS 10.3-10.6; E8).

A recipe is configuration, not a fork: `command: agentkeys run --server akref:… -- <server>` with
reference-only env. Validation refuses anything else, so a drifted recipe fails instead of silently
bypassing the broker.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from agentkeys.core.resolution import ResolutionCore
from agentkeys.egress.contract import Injection, InjectionRequest
from agentkeys.egress.env import EnvInjector
from agentkeys.egress.header import HeaderInjector
from agentkeys.redact import looks_like_secret

__all__ = [
    "RECIPES",
    "Recipe",
    "RecipeError",
    "SmokeResult",
    "get_recipe",
    "render_mcp_wiring",
    "run_recipe_smoke",
    "support_label",
    "validate_wiring",
]

_REFERENCE_PREFIXES = ("akref:", "op://")


class RecipeError(Exception):
    """The wiring does not route through the broker (or carries a secret)."""


@dataclass(frozen=True)
class Recipe:
    """One harness wiring recipe; `supported=False` is an honest "not yet"."""

    name: str
    tier: int
    harness: str
    config_file: str
    egress_kind: str
    docs: str
    supported: bool = True


RECIPES: dict[str, Recipe] = {
    "claude-code": Recipe(
        name="claude-code",
        tier=1,
        harness="Claude Code",
        config_file=".mcp.json",
        egress_kind="env",
        docs="docs/guides/recipes/claude-code.md",
    ),
    "cursor": Recipe(
        name="cursor",
        tier=1,
        harness="Cursor",
        config_file=".cursor/mcp.json",
        egress_kind="header",
        docs="docs/guides/recipes/cursor.md",
    ),
    "generic-mcp": Recipe(
        name="generic-mcp",
        tier=2,
        harness="any stdio MCP client",
        config_file="client config",
        egress_kind="env",
        docs="docs/guides/recipes/generic.md",
    ),
    "generic-http": Recipe(
        name="generic-http",
        tier=2,
        harness="any HTTP API",
        config_file="client config",
        egress_kind="header",
        docs="docs/guides/recipes/generic.md",
    ),
    "generic-exchange": Recipe(
        name="generic-exchange",
        tier=2,
        harness="RFC 8693 target",
        config_file="client config",
        egress_kind="exchange",
        docs="docs/guides/recipes/generic.md",
    ),
    "generic-cli": Recipe(
        name="generic-cli",
        tier=2,
        harness="plain CLI",
        config_file="shell",
        egress_kind="env",
        docs="docs/guides/recipes/generic.md",
    ),
    "jetbrains": Recipe(
        name="jetbrains",
        tier=3,
        harness="JetBrains IDE MCP",
        config_file="n/a",
        egress_kind="unknown",
        docs="docs/guides/recipes/generic.md",
        supported=False,
    ),
}


def get_recipe(name: str) -> Recipe:
    """Look up a recipe by name; unknown names are a usage error."""
    if name not in RECIPES:
        raise RecipeError(f"unknown recipe: {name}")
    return RECIPES[name]


def support_label(recipe: Recipe) -> str:
    """The honest PRD 19 label; an uncovered harness is never called supported."""
    return (
        f"{recipe.harness}: supported (Tier-{recipe.tier})"
        if recipe.supported
        else (f"{recipe.harness}: not yet (no interception point documented)")
    )


def render_mcp_wiring(
    recipe: Recipe,
    *,
    server: str = "agentkeys",
    reference: str = "akref:file/agentkeys/dev/token",
    server_command: str = "<server-command>",
) -> dict[str, Any]:
    """The one wiring shape every MCP recipe uses (no per-harness fork)."""
    return {
        "mcpServers": {
            server: {
                "command": "agentkeys",
                "args": ["run", "--server", reference, "--", server_command],
                "env": {},
            }
        }
    }


def _wiring_problems(wiring: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    servers = wiring.get("mcpServers")
    if not isinstance(servers, Mapping) or len(servers) != 1:
        return ["wiring must declare exactly one mcpServers entry"]
    entry = next(iter(servers.values()))
    if not isinstance(entry, Mapping):
        return ["mcpServers entry must be an object"]
    if entry.get("command") != "agentkeys":
        problems.append("command must be 'agentkeys' (the broker wrapper, no harness fork)")
    args = entry.get("args")
    if not isinstance(args, list) or not args or args[0] != "run":
        problems.append("args must start with 'run'")
    elif "--server" not in args:
        problems.append("args must pass --server <akref:…>")
    else:
        index = args.index("--server")
        reference = args[index + 1] if index + 1 < len(args) else ""
        if not isinstance(reference, str) or not reference.startswith(_REFERENCE_PREFIXES):
            problems.append("--server must name a reference (akref:…), never a value")
    env = entry.get("env", {})
    if not isinstance(env, Mapping):
        problems.append("env must be an object")
    else:
        for key, value in env.items():
            if not isinstance(value, str):
                problems.append(f"env.{key} must be a string")
                continue
            if looks_like_secret(value):
                problems.append(f"env.{key} carries a secret value; env must be reference-only")
            elif value and not value.startswith(_REFERENCE_PREFIXES):
                problems.append(f"env.{key} must hold a reference (akref:…), not a literal")
    return problems


def validate_wiring(recipe: Recipe, wiring: Mapping[str, Any]) -> None:
    """Raise `RecipeError` for anything that would bypass or leak (SC-35/SC-36)."""
    if not recipe.supported:
        raise RecipeError(support_label(recipe))
    problems = _wiring_problems(wiring)
    if problems:
        raise RecipeError(f"{recipe.name}: " + "; ".join(problems))


@dataclass(frozen=True)
class SmokeResult:
    """The recipe's end-to-end smoke: authenticated or not, and what the transcript held."""

    ok: bool
    kind: str
    transcript: tuple[str, ...]


def run_recipe_smoke(
    recipe: Recipe,
    core: ResolutionCore,
    *,
    session_id: str,
    reference_id: str,
    audience: str,
    tool: str,
    target: Callable[[Injection], bool],
) -> SmokeResult:
    """Resolve via the broker, inject at the recipe egress, let the target authenticate."""
    if not recipe.supported:
        raise RecipeError(support_label(recipe))
    resolved = core.resolve(reference_id, audience=audience, tool=tool, session_id=session_id)
    request = InjectionRequest(audience=audience, tool=tool)
    if recipe.egress_kind == "header":
        injection = HeaderInjector(audience).apply(resolved, request=request)
    elif recipe.egress_kind == "env":
        injection = EnvInjector(audience).apply(resolved, request=request)
    else:
        raise RecipeError(
            f"{recipe.name}: egress {recipe.egress_kind!r} needs a live target; "
            "this smoke covers env and header only"
        )
    transcript = (reference_id,)
    return SmokeResult(ok=bool(target(injection)), kind=injection.kind, transcript=transcript)
