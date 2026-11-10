"""HTTP header driver: overwrite any client credential with the bound token
(M4, WBS 4.3)."""

from __future__ import annotations

from agentkeys.backends.contract import SecretValue
from agentkeys.core.resolution import ResolvedIssuance
from agentkeys.egress.contract import BaseInjector, Injection, InjectionRequest

__all__ = ["HeaderInjector"]

CREDENTIAL_HEADERS = ("authorization", "proxy-authorization", "x-api-key", "api-key")


class HeaderInjector(BaseInjector):
    """Sets `<header>: <scheme> <bound-token>`, removing client-supplied credential headers."""

    kind = "header"

    def __init__(
        self, audience: str, header: str = "Authorization", scheme: str = "Bearer"
    ) -> None:
        super().__init__(audience)
        self.header = header
        self.scheme = scheme

    def _deliver(self, resolved: ResolvedIssuance, request: InjectionRequest) -> Injection:
        value = resolved.token or ""
        headers = {
            name: header_value
            for name, header_value in request.client_headers.items()
            if name.lower() not in CREDENTIAL_HEADERS
        }
        headers[self.header] = f"{self.scheme} {value}".strip()
        return Injection(
            kind=self.kind,
            audience=self.target_audience(),
            secret=SecretValue(value),
            headers=headers,
            overwrote_client_credential=any(
                name.lower() in CREDENTIAL_HEADERS for name in request.client_headers
            ),
        )
