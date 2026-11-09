# agentkeys — development targets. Runtime is stdlib-only; these are dev conveniences.

PYTHON ?= python3
VENV ?= .venv
COV_MIN ?= 95

# Use the venv's tools when present; otherwise fall back to PATH (as in CI).
ifeq ($(wildcard $(VENV)/bin/ruff),)
BIN :=
else
BIN := $(VENV)/bin/
endif

.PHONY: setup lint typecheck test cov gate clean

setup: ## create the dev environment and install the package (editable) + dev extras
	python3 -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install -e ".[dev]"

lint: ## ruff, zero violations
	$(BIN)/ruff check src tests
	$(BIN)/ruff format --check src tests

typecheck: ## mypy --strict
	$(BIN)/mypy

test: ## run the test suite
	$(BIN)/pytest

cov: ## run tests with coverage and enforce the milestone floor
	$(BIN)/pytest --cov=agentkeys --cov-report=term-missing --cov-fail-under=$(COV_MIN)

gate: lint typecheck cov ## the standing milestone gate

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +