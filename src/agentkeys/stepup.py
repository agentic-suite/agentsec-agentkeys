"""Step-up issuance: ask agentpolicy, record the decision, never decide it ourselves (M10, R9).

The broker is the courier, not the approver: a decision must come from a named decision source,
be one of `allow|deny|timeout`, and never be the requesting agent approving itself.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

__all__ = [
    "DECISIONS",
    "AgentPolicyClient",
    "PolicyClient",
    "PolicyDecision",
    "PolicyError",
    "StepUpDenied",
    "StepUpGate",
    "StepUpRequest",
]

DECISIONS: tuple[str, ...] = ("allow", "deny", "timeout")
Decision = Literal["allow", "deny", "timeout"]


class PolicyError(Exception):
    """A decision outside the contract (unknown verdict, empty source, self-approval)."""


@dataclass(frozen=True)
class StepUpRequest:
    """What is being asked for: the reference, class, binding, and who is asking."""

    reference_id: str
    class_: str
    session_id: str
    agent_id: str
    principal: str
    audience: str
    tool: str
    requested_at: int


@dataclass(frozen=True)
class PolicyDecision:
    """agentpolicy's answer: the verdict, who decided, and the human provenance class."""

    decision: str
    decided_by: str
    source: str
    reason: str | None = None
    decided_at: int = 0


class PolicyClient(Protocol):
    """The only way a decision enters the broker."""

    def ask(self, request: StepUpRequest) -> PolicyDecision: ...


class AgentPolicyClient:
    """Asks agentpolicy over an injected transport; validates the answer, never edits it."""

    def __init__(self, ask_fn: Callable[[StepUpRequest], PolicyDecision]) -> None:
        self._ask_fn = ask_fn

    def ask(self, request: StepUpRequest) -> PolicyDecision:
        decision = self._ask_fn(request)
        if decision.decision not in DECISIONS:
            raise PolicyError(
                f"invalid decision {decision.decision!r}; agentpolicy must answer "
                f"{'|'.join(DECISIONS)}"
            )
        if not decision.decided_by:
            raise PolicyError("a decision must name its decision source")
        if decision.decided_by == request.agent_id:
            raise PolicyError("the requesting agent cannot approve its own issuance")
        if not decision.source:
            raise PolicyError("a decision must carry authorization.source")
        return decision


class StepUpDenied(Exception):
    """No approval (deny, timeout, or a malformed decision) — no credential is minted."""

    def __init__(self, reason: str, decision: PolicyDecision | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.decision = decision


class StepUpGate:
    """Gates the configured classes behind a live policy decision."""

    def __init__(
        self,
        policy: PolicyClient,
        *,
        gated_classes: tuple[str, ...] = ("prod",),
        clock: Callable[[], int] | None = None,
    ) -> None:
        self._policy = policy
        self._gated = frozenset(gated_classes)
        self._clock = clock or (lambda: int(time.time()))

    def is_gated(self, class_: str) -> bool:
        return class_ in self._gated

    def authorize(self, request: StepUpRequest) -> PolicyDecision:
        try:
            decision = self._policy.ask(request)
        except PolicyError as exc:
            raise StepUpDenied(f"policy-error: {exc}") from exc
        if decision.decision != "allow":
            raise StepUpDenied(f"{decision.decision}: {decision.reason or 'no approval'}", decision)
        return decision
