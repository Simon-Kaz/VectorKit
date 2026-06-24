# Local development entry points. Run `make help` for the list.
# Everything here also runs in CI, so green locally == green in CI.

.DEFAULT_GOAL := help
.PHONY: help setup hooks lint format test check ci clean

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## Create venv and install dev dependencies + the package
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "Done. Activate with: . $(VENV)/bin/activate"

hooks: ## Install git pre-commit and pre-push hooks
	$(VENV)/bin/pre-commit install --install-hooks
	$(VENV)/bin/pre-commit install --hook-type pre-push
	@echo "Hooks installed."

lint: ## Lint (ruff) without modifying files
	$(VENV)/bin/ruff check .

format: ## Auto-format and auto-fix lint issues
	$(VENV)/bin/ruff format .
	$(VENV)/bin/ruff check --fix .

test: ## Run the test suite
	./scripts/run-tests.sh

check: ## Run ALL hooks against ALL files (what to run before pushing)
	$(VENV)/bin/pre-commit run --all-files --hook-stage pre-push
	$(VENV)/bin/pre-commit run --all-files

ci: lint test ## The validation CI runs (lint + format check + tests)
	$(VENV)/bin/ruff format --check .

clean: ## Remove caches and the venv
	rm -rf $(VENV) .pytest_cache .ruff_cache
	find . -path ./libs/vendor -prune -o -name '__pycache__' -type d -print | xargs rm -rf
