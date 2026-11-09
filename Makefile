# agentkeys — development targets. Runtime is stdlib-only; these are dev conveniences.

VENV ?= .venv
COV_MIN ?= 95

# Use the project venv when it exists (local), else the interpreter on PATH (as in CI).
PYTHON ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)

.PHONY: setup lint typecheck test cov gate clean

setup: ## create the dev environment and install the package (editable) + dev extras
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install -e ".[dev]"

lint: ## ruff, zero violations
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m ruff format --check src tests

typecheck: ## mypy --strict
	$(PYTHON) -m mypy

test: ## run the test suite
	$(PYTHON) -m pytest

cov: ## run tests with coverage and enforce the milestone floor
	$(PYTHON) -m pytest --cov=agentkeys --cov-report=term-missing --cov-fail-under=$(COV_MIN)

gate: lint typecheck cov ## the standing milestone gate

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +