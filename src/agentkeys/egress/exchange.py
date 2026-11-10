"""RFC 8693 driver: exchange to a narrow, audience-bound token with `act` (M4, WBS 4.4)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from agentkeys.backends.contract import SecretValue
from agentkeys.core.resolution import ResolvedIssuance
from agentkeys.egress.contract import (
    BaseInjector,
    Injection,
    InjectionDenied,
    InjectionRequest,
)

__all__ = ["ExchangeCall", "ExchangeInjector"]

GRANT_TYPE = "urn:ietf:params:oauth:grant-type:token-exchange"
ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"  # noqa: S105 - a URN type

ExchangeCall = Callable[[Mapping[str, str]], Mapping[str, Any]]


class ExchangeInjector(BaseInjector):
    """Performs a token exchange for one audience, one tool scope, and an actor identity."""

    kind = "exchange"

    def __init__(
        self,
        audience: str,
        exchange_fn: ExchangeCall,
        *,
        actor_token: str = "agentkeys:broker",  # noqa: S107 - an actor identifier, not a secret
        actor: str = "agent",
    ) -> None:
        super().__init__(audience)
        self._exchange = exchange_fn
        self._actor_token = actor_token
        self.actor = actor

    def request_body(self, resolved: ResolvedIssuance, request: InjectionRequest) -> dict[str, str]:
        """The exact exchange request; the client's token is never part of it."""
        return {
            "grant_type": GRANT_TYPE,
            "subject_token": resolved.token or "",
            "subject_token_type": ACCESS_TOKEN_TYPE,
            "requested_token_type": ACCESS_TOKEN_TYPE,
            "audience": self.target_audience(),
            "scope": request.tool,
            "actor_token": self._actor_token,
        }

    def _deliver(self, resolved: ResolvedIssuance, request: InjectionRequest) -> Injection:
        body = self.request_body(resolved, request)
        if request.client_token is not None and request.client_token in body.values():
            raise InjectionDenied(
                "passthrough-stripped", "the client token must never be the exchange subject"
            )
        response = self._exchange(body)
        returned = response.get("access_token")
        if not isinstance(returned, str) or not returned:
            raise InjectionDenied("injector-unavailable", "exchange returned no access token")
        exchanged = SecretValue(returned)
        return Injection(
            kind=self.kind,
            audience=self.target_audience(),
            secret=exchanged,
            token=exchanged,
            actor=str(response.get("act") or self.actor),
        )
