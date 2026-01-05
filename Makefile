.PHONY: format format-check lint prettier prettier-check ty upgrade-ty test py-fast-ci fast-ci all-ci md-check docs-validate docs-sync-check docs-fix clean publish fix reinstall-erk-tools

prettier:
	prettier --write '**/*.md' --ignore-path .gitignore

prettier-check:
	prettier --check '**/*.md' --ignore-path .gitignore

format:
	uv run ruff format

format-check:
	uv run ruff format --check

lint:
	uv run ruff check

fix:
	uv run ruff check --fix --unsafe-fixes

ty:
	uv run ty check

upgrade-ty:
	uv remove ty --group dev && uv add --dev ty

# === Package-specific test targets ===

test-erk-dev:
	cd packages/erk-dev && uv run pytest -n auto

# === Erk test targets ===

# Unit tests: Fast, in-memory tests using fakes (tests/unit/, tests/commands/, tests/core/)
# These provide quick feedback for development iteration
test-unit-erk:
	uv run pytest tests/unit/ tests/commands/ tests/core/ -n auto

# Integration tests: Slower tests with real I/O and subprocess calls (tests/integration/)
# These verify that abstraction layers correctly wrap external tools
test-integration-erk:
	uv run pytest tests/integration/ -n auto

# All erk tests (unit + integration)
test-all-erk: test-unit-erk test-integration-erk

# Backward compatibility: test-erk now runs unit tests only
test-erk: test-unit-erk

# === Combined test targets ===

# Default 'make test': Run unit tests only (fast feedback loop for development)
# Includes: erk unit tests + all erk-dev tests
test: test-unit-erk test-erk-dev

# Integration tests: Run only integration tests across all packages
test-integration: test-integration-erk

# All tests: Run both unit and integration tests (comprehensive validation)
test-all: test-all-erk test-erk-dev

md-check:
	uv run erk md check

docs-validate:
	uv run erk docs validate

docs-sync-check:
	uv run erk docs sync --check

docs-fix:
	uv run erk docs sync

# Python-only Fast CI: Lint, format, type check, and unit tests (skips markdown checks)
py-fast-ci:
	@echo "=== Python Fast CI ===" && \
	exit_code=0; \
	echo "\n--- Lint ---" && uv run ruff check || exit_code=1; \
	echo "\n--- Format Check ---" && uv run ruff format --check || exit_code=1; \
	echo "\n--- ty ---" && uv run ty check || exit_code=1; \
	echo "\n--- Unit Tests (erk) ---" && uv run pytest tests/unit/ tests/commands/ tests/core/ -n auto || exit_code=1; \
	echo "\n--- Tests (erk-dev) ---" && uv run pytest packages/erk-dev -n auto || exit_code=1; \
	echo "\n--- Tests (erk-statusline) ---" && uv run pytest packages/erk-statusline -n auto || exit_code=1; \
	exit $$exit_code

# Fast CI: Run all checks with unit tests only (fast feedback loop)
fast-ci:
	@echo "=== Fast CI ===" && \
	exit_code=0; \
	echo "\n--- Lint ---" && uv run ruff check || exit_code=1; \
	echo "\n--- Format Check ---" && uv run ruff format --check || exit_code=1; \
	echo "\n--- Prettier Check ---" && prettier --check '**/*.md' --ignore-path .gitignore || exit_code=1; \
	echo "\n--- Markdown Check ---" && uv run erk md check || exit_code=1; \
	echo "\n--- ty ---" && uv run ty check || exit_code=1; \
	echo "\n--- Unit Tests (erk) ---" && uv run pytest tests/unit/ tests/commands/ tests/core/ -n auto || exit_code=1; \
	echo "\n--- Tests (erk-dev) ---" && uv run pytest packages/erk-dev -n auto || exit_code=1; \
	echo "\n--- Tests (erk-statusline) ---" && uv run pytest packages/erk-statusline -n auto || exit_code=1; \
	exit $$exit_code

# CI target: Run all tests (unit + integration) for comprehensive validation
all-ci:
	@echo "=== All CI ===" && \
	exit_code=0; \
	echo "\n--- Lint ---" && uv run ruff check || exit_code=1; \
	echo "\n--- Format Check ---" && uv run ruff format --check || exit_code=1; \
	echo "\n--- Prettier Check ---" && prettier --check '**/*.md' --ignore-path .gitignore || exit_code=1; \
	echo "\n--- Markdown Check ---" && uv run erk md check || exit_code=1; \
	echo "\n--- ty ---" && uv run ty check || exit_code=1; \
	echo "\n--- Unit Tests (erk) ---" && uv run pytest tests/unit/ tests/commands/ tests/core/ -n auto || exit_code=1; \
	echo "\n--- Integration Tests (erk) ---" && uv run pytest tests/integration/ -n auto || exit_code=1; \
	echo "\n--- Tests (erk-dev) ---" && uv run pytest packages/erk-dev -n auto || exit_code=1; \
	echo "\n--- Tests (erk-statusline) ---" && uv run pytest packages/erk-statusline -n auto || exit_code=1; \
	exit $$exit_code

# Clean build artifacts and Python caches
clean:
	rm -rf dist/*.whl dist/*.tar.gz
	find . -type d -name "__pycache__" -exec rm -rf {} + || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + || true
	find . -type f -name "*.pyc" -delete || true
	find . -type f -name "*.pyo" -delete || true
	find . -type f -name ".coverage" -delete || true
	rm -rf htmlcov/ .coverage.* || true
	find . -type d -empty -delete || true

# Build erk package
build: clean
	uv build --package erk -o dist

# Reinstall erk tools in editable mode
reinstall-erk-tools:
	uv tool install --force -e .

# Publish packages to PyPI
# Use erk-dev publish-to-pypi command instead (recommended)
publish: build
	erk-dev publish-to-pypi

pull_master:
	git -C /Users/schrockn/code/erk pull origin master
