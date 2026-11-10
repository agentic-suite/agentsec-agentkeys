"""Claims lint for the release gate (M15, 15.2; PRD 20 sections 6-7).

The rule: **never use a stronger word than the evidence supports.** It is enforced two ways, because
either alone is theatre:

* **The ledger** (`docs/release/v0.1.0/CLAIMS.md`) is the machine-checkable list of public claims.
  Every label must be in the ladder, every claim above *documented* must resolve to a **committed
  field result**, and a WARN result may not carry *field-tested* - a bounded truth is not a full
  one.
* **The prose** is scanned for superlatives that no evidence can support at v0.1.0 (*certified*,
  *militarily hardened*, ...) and for non-claims that must stay present.

`verified` is not a compliment; it means a third party reproduced the claim. At v0.1.0 nothing is
verified.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "BANNED",
    "LADDER",
    "Claim",
    "Finding",
    "lint_claims",
    "lint_compat",
    "load_ledger",
    "public_files",
    "rank",
    "results_index",
    "scan_prose",
]

# Ordered weakest → strongest. A label may never outrank its evidence.
LADDER = ("documented", "conformance", "field-tested", "verified")

# Words that assert a standing we do not have. Matched case-insensitively.
BANNED = (
    "SOC 2 certified",
    "ISO 27001 certified",
    "certified secure",
    "enterprise-grade",
    "militarily",
    "bank-grade",
    "unhackable",
    "guaranteed secure",
    "production-ready",
)

# A negation in the same sentence makes a banned term a *non-claim* ("we are not certified"),
# which is the honest usage we want to keep. Deliberately narrow.
_NEGATIONS = (" not ", "n't ", "no ", "never ", "non-", "neither ", "nor ")

_STATUSES = ("pass", "warn", "fail", "not-run")

_PUBLIC_GLOBS = (
    "README.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "docs/release/v0.1.0/*.md",
    "docs/reference/*.md",
    "docs/guides/*.md",
    "docs/guides/recipes/*.md",
    "docs/explanation/*.md",
)


@dataclass(frozen=True)
class Claim:
    """One public claim, as recorded in the ledger."""

    text: str
    label: str
    evidence: tuple[str, ...] = ()
    third_party: bool = False
    note: str = ""


@dataclass(frozen=True)
class Finding:
    """One reason the lint refuses to be green."""

    claim: str
    problem: str
    path: str = ""

    def __str__(self) -> str:  # pragma: no cover - formatting only
        where = f" ({self.path})" if self.path else ""
        return f"{self.claim}{where}: {self.problem}"


def rank(label: str) -> int:
    """The strength of a label; an unknown label is a caller error, never silently weak."""
    try:
        return LADDER.index(label)
    except ValueError as exc:
        raise ValueError(f"unknown label: {label!r}") from exc


def results_index(results_dir: str | Path) -> dict[str, str]:
    """Map every committed case id to its committed status, read from the results tree."""
    import json

    index: dict[str, str] = {}
    base = Path(results_dir)
    if not base.is_dir():
        return index
    for summary in sorted(base.glob("*/summary.json")):
        try:
            payload = json.loads(summary.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(payload, dict) and isinstance(payload.get("status"), str):
            index[str(payload.get("case") or summary.parent.name)] = payload["status"]
    return index


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def load_ledger(path: str | Path) -> tuple[Claim, ...]:
    """Parse the ledger's markdown table into claims.

    Columns: ``Claim | Label | Evidence | Third party | Note``. The ``Evidence`` cell lists case ids
    (``-`` for none). Rows outside a table are ignored, so the file stays readable prose plus one
    checked table.
    """
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    claims: list[Claim] = []
    in_table = False
    for line in lines:
        if not line.strip().startswith("|"):
            in_table = False
            continue
        cells = _cells(line)
        if not cells or set("".join(cells)) <= set("-: "):
            continue
        if [cell.lower() for cell in cells[:3]] == ["claim", "label", "evidence"]:
            in_table = True
            continue
        if not in_table or len(cells) < 3:
            continue
        evidence_cell = cells[2]
        ids = tuple(re.findall(r"FT-[A-Z0-9-]+", evidence_cell))
        third_party = len(cells) > 3 and cells[3].strip().lower() in {"yes", "true", "y"}
        note = cells[4] if len(cells) > 4 else ""
        claims.append(
            Claim(
                text=cells[0].replace("**", "").strip(),
                label=cells[1].replace("*", "").strip().lower(),
                evidence=ids,
                third_party=third_party,
                note=note,
            )
        )
    return tuple(claims)


def lint_claims(claims: Sequence[Claim], index: Mapping[str, str]) -> tuple[Finding, ...]:
    """Check every claim's label against the evidence it names."""
    findings: list[Finding] = []
    for claim in claims:
        try:
            strength = rank(claim.label)
        except ValueError:
            findings.append(Finding(claim.text, f"unknown label: {claim.label!r}"))
            continue

        if strength == 0:
            # `documented` needs nothing beyond being written down — but a WARN behind it must still
            # say what the limitation is, or the row is a euphemism rather than a label.
            warn = [case for case in claim.evidence if index.get(case) == "warn"]
            if warn and not claim.note:
                findings.append(
                    Finding(
                        claim.text, f"WARN evidence {warn[0]} must state its limitation in Note"
                    )
                )
            continue

        if not claim.evidence:
            findings.append(
                Finding(
                    claim.text, "no evidence: a label above *documented* must name a field result"
                )
            )
            continue

        statuses: list[str] = []
        for case in claim.evidence:
            status = index.get(case)
            if status is None:
                findings.append(Finding(claim.text, f"no committed result for {case}"))
                continue
            statuses.append(status)
            if status not in _STATUSES:
                findings.append(
                    Finding(claim.text, f"evidence {case} has unknown status {status!r}")
                )
                continue
            if status == "fail":
                findings.append(Finding(claim.text, f"evidence {case} is a fail"))
            elif status == "not-run":
                findings.append(Finding(claim.text, f"evidence {case} was not run"))
            elif status == "warn" and strength > rank("documented"):
                findings.append(
                    Finding(
                        claim.text,
                        f"evidence {case} is a WARN — a bounded truth earns *documented*, "
                        f"not *{claim.label}*",
                    )
                )
                if not claim.note:
                    findings.append(
                        Finding(
                            claim.text, f"WARN evidence {case} must state its limitation in Note"
                        )
                    )

        if claim.label == "verified" and not claim.third_party:
            findings.append(
                Finding(
                    claim.text, "*verified* requires an independent third party to reproduce it"
                )
            )
        if claim.label == "conformance" and statuses and all(s != "pass" for s in statuses):
            findings.append(Finding(claim.text, "*conformance* needs at least one passing suite"))
    return tuple(findings)


def public_files(root: str | Path) -> dict[str, str]:
    """The files whose prose counts as a public claim."""
    base = Path(root)
    found: dict[str, str] = {}
    for pattern in _PUBLIC_GLOBS:
        for path in sorted(base.glob(pattern)):
            if path.is_file():
                found[str(path.relative_to(base))] = path.read_text(encoding="utf-8")
    return found


def _sentences(text: str) -> Iterable[str]:
    for line in text.splitlines():
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            if sentence.strip():
                yield sentence


def scan_prose(files: Mapping[str, str]) -> tuple[Finding, ...]:
    """Find banned superlatives that are not part of a non-claim."""
    findings: list[Finding] = []
    for path, text in files.items():
        for sentence in _sentences(text):
            lowered = sentence.lower()
            if any(negation in lowered for negation in _NEGATIONS):
                continue
            for term in BANNED:
                if term.lower() in lowered:
                    findings.append(Finding(sentence.strip()[:120], f"banned claim: {term}", path))
    return tuple(findings)


def lint_compat(doc: str, index: Mapping[str, str]) -> tuple[Finding, ...]:
    """No compatibility row may say *supported*/*first-class* without a green pack behind it."""
    findings: list[Finding] = []
    green = {"supported", "first-class", "first-class recipe"}
    for line in doc.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) < 3 or set("".join(cells)) <= set("-: "):
            continue
        label = cells[1].lower().replace("*", "").strip()
        if label not in green:
            continue
        case = re.search(r"FT-[A-Z0-9-]+", cells[2])
        if case is None:
            findings.append(Finding(cells[0], f"'{label}' with no evidence case"))
            continue
        if index.get(case.group(0)) != "pass":
            findings.append(
                Finding(
                    cells[0],
                    f"'{label}' claimed on {case.group(0)} which is "
                    f"{index.get(case.group(0), 'not run')} — lower the label",
                )
            )
    return tuple(findings)
