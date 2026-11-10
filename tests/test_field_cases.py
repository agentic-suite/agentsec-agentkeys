"""The field-test registry is wired: 74 cases, unique ids, full trace mappings."""

from __future__ import annotations

from agentkeys.fieldtest.cases import CASES_PATH, load_cases
from agentkeys.fieldtest.registry import EXECUTORS, load_registry, packs
from agentkeys.fieldtest.trace import MAPPINGS

EXPECTED_COUNT = 74
EXPECTED_PACKS = {
    "docker",
    "core",
    "binding",
    "stdio",
    "evasion",
    "failclosed",
    "killtime",
    "audit",
    "stepup",
    "harness",
    "offline",
    "attack",
    "migrate",
    "ops",
    "nfr",
    "conformance",
}


def test_the_registry_has_the_frozen_seventy_four_cases() -> None:
    cases = load_registry()
    assert len(cases) == EXPECTED_COUNT
    assert len({case.id for case in cases}) == EXPECTED_COUNT


def test_every_cases_yaml_id_has_an_executor_and_vice_versa() -> None:
    yaml_ids = {case.id for case in load_cases(CASES_PATH)}
    assert yaml_ids == set(EXECUTORS)


def test_the_pack_set_is_the_plan_pack_set() -> None:
    assert set(packs()) == EXPECTED_PACKS


def test_every_case_has_a_trace_mapping() -> None:
    assert {case.id for case in load_registry()} == set(MAPPINGS)


def test_the_five_blocking_cases_are_registered() -> None:
    blocking = {case.id for case in load_registry() if case.blocking}
    assert blocking == {
        "FT-RK-KILLTIME",
        "FT-AP-CONTEXTDUMP",
        "FT-AP-TAMPER",
        "FT-AP-EVIDENCE",
        "FT-MP-SCANMIGRATE",
    }


def test_every_case_has_a_pack_class_and_driver() -> None:
    for case in load_registry():
        assert case.pack in EXPECTED_PACKS
        assert case.klass in {"P/F", "P/F|W"}
        assert case.driver
        assert case.env
