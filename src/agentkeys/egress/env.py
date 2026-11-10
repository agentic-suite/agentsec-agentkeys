"""env-virtualization driver: the scoped value reaches a child at its own egress (M4, WBS 4.2)."""

from __future__ import annotations

from collections.abc import Mapping

from agentkeys.backends.contract import SecretValue
from agentkeys.core.resolution import ResolvedIssuance
from agentkeys.egress.contract import BaseInjector, Injection, InjectionRequest

__all__ = ["EnvInjector"]

DEFAULT_VARIABLE = "AGENTKEYS_SCOPED_TOKEN"


class EnvInjector(BaseInjector):
    """Applies the issuance to a child-process environment; the parent never holds it."""

    kind = "env"

    def __init__(self, audience: str, variable: str = DEFAULT_VARIABLE) -> None:
        super().__init__(audience)
        if not variable.isidentifier():
            raise ValueError(f"invalid environment variable name: {variable!r}")
        self.variable = variable

    def _deliver(self, resolved: ResolvedIssuance, request: InjectionRequest) -> Injection:
        value = resolved.token or ""
        env: Mapping[str, str] = {self.variable: value}
        return Injection(
            kind=self.kind,
            audience=self.target_audience(),
            secret=SecretValue(value),
            env=env,
        )
