.PHONY: format format-check lint prettier prettier-check pyright upgrade-pyright test fast-ci all-ci check md-check clean prepare publish fix reinstall-erk-tools

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

pyright:
	uv run pyright

upgrade-pyright:
	uv remove pyright --group dev && uv add --dev pyright

# === Package-specific test targets ===

test-erk-dev:
	cd packages/erk-dev && uv run pytest -n auto

# Unit tests: Fast, in-memory tests using fakes
test-unit-dot-agent-kit:
	cd packages/dot-agent-kit && uv run pytest tests/unit/ -n auto

# Integration tests: Slower tests with real I/O and subprocess calls
test-integration-dot-agent-kit:
	cd packages/dot-agent-kit && uv run pytest tests/integration/ -n auto

# Backward compatibility: test-dot-agent-kit now runs unit tests only
test-dot-agent-kit: test-unit-dot-agent-kit

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
# Includes: erk unit tests + all erk-dev tests + all dot-agent-kit tests
test: test-unit-erk test-erk-dev test-dot-agent-kit

# Integration tests: Run only integration tests across all packages
test-integration: test-integration-erk test-integration-dot-agent-kit

# All tests: Run both unit and integration tests (comprehensive validation)
test-all: test-all-erk test-erk-dev test-unit-dot-agent-kit test-integration-dot-agent-kit

check:
	uv run dot-agent check

md-check:
	uv run dot-agent md check --check-links --exclude "packages/*/src/*/data/kits"

# Removed: land-branch command has been deprecated
# Removed: sync-dignified-python-universal (obsolete - shared content now referenced directly)

# Fast CI: Run all checks with unit tests only (fast feedback loop)
fast-ci: lint format-check prettier-check md-check pyright test check

# CI target: Run all tests (unit + integration) for comprehensive validation
all-ci: lint format-check prettier-check md-check pyright test-all check

# Clean build artifacts
clean:
	rm -rf dist/*.whl dist/*.tar.gz

# Build erk and dot-agent-kit packages
build: clean
	uv build --package dot-agent-kit -o dist
	uv build --package erk -o dist

# Reinstall erk and dot-agent tools in editable mode
reinstall-erk-tools:
	uv tool install --force -e .
	cd packages/dot-agent-kit && uv tool install --force -e .

# Prepare release: bump versions, build artifacts (user commits manually)
prepare:
	erk-dev prepare-release

# Publish release: upload prepared artifacts to PyPI (requires prior prepare + commit)
publish:
	erk-dev publish-release
