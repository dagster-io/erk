.PHONY: format format-check lint prettier prettier-check pyright upgrade-pyright test py-fast-ci fast-ci all-ci check kit-build kit-build-autofix kit-build-check md-check kit-md-check docs-validate docs-sync-check clean publish fix reinstall-erk-tools

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
test-unit-erk-kits:
	cd packages/erk-kits && uv run pytest tests/unit/ -n auto

# Integration tests: Slower tests with real I/O and subprocess calls
test-integration-erk-kits:
	cd packages/erk-kits && uv run pytest tests/integration/ -n auto

# Backward compatibility: test-erk-kits now runs unit tests only
test-erk-kits: test-unit-erk-kits

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
# Note: erk-kits has no unit tests yet, so it's excluded from this target
test: test-unit-erk test-erk-dev

# Integration tests: Run only integration tests across all packages
# Note: erk-kits has no integration tests (wheel packaging tests are in tests/integration/kits/)
test-integration: test-integration-erk

# All tests: Run both unit and integration tests (comprehensive validation)
test-all: test-all-erk test-erk-dev

check:
	uv run erk kit check

# Build kits: Copy artifacts from source locations to kit packages
kit-build:
	uv run erk dev kit-build

# Auto-fix kit build: build and commit if changed
kit-build-autofix:
	@uv run erk dev kit-build && \
	git add packages/erk-kits/src/erk_kits/data/kits/ && \
	if [ -n "$$(git diff --cached --name-only)" ]; then \
		echo "Kit artifacts changed, auto-committing..."; \
		git commit -m "Auto-fix: Sync kit artifacts with sources"; \
	fi

# Validate kits: Check that artifacts match source locations
kit-build-check:
	uv run erk dev kit-build --check

md-check:
	uv run erk md check --check-links --exclude "packages/*/src/*/data/kits" --exclude ".impl" --exclude ".worker-impl"

# Kit markdown check: Validate @ references in kit data files
# These are excluded from md-check because they may have template-style references,
# but we still want to validate that actual file includes are correct
# NOTE: cd is required because the command validates from the current directory
kit-md-check:
	cd packages/erk-kits/src/erk_kits/data/kits && uv run erk md check --check-links

docs-validate:
	uv run erk docs validate

docs-sync-check:
	uv run erk docs sync --check

# Removed: land-branch command has been deprecated
# Removed: sync-dignified-python-universal (obsolete - shared content now referenced directly)

# Python-only Fast CI: Lint, type check, and unit tests (skips formatting/markdown checks)
py-fast-ci:
	@echo "=== Python Fast CI ===" && \
	exit_code=0; \
	echo "\n--- Lint ---" && uv run ruff check || exit_code=1; \
	echo "\n--- Pyright ---" && uv run pyright || exit_code=1; \
	echo "\n--- Unit Tests (erk) ---" && uv run pytest tests/unit/ tests/commands/ tests/core/ -n auto || exit_code=1; \
	echo "\n--- Tests (erk-dev) ---" && uv run pytest packages/erk-dev -n auto || exit_code=1; \
	exit $$exit_code

# Fast CI: Run all checks with unit tests only (fast feedback loop)
fast-ci:
	@echo "=== Fast CI ===" && \
	exit_code=0; \
	echo "\n--- Lint ---" && uv run ruff check || exit_code=1; \
	echo "\n--- Format Check ---" && uv run ruff format --check || exit_code=1; \
	echo "\n--- Prettier Check ---" && prettier --check '**/*.md' --ignore-path .gitignore || exit_code=1; \
	echo "\n--- Markdown Check ---" && uv run erk md check --check-links --exclude "packages/*/src/*/data/kits" --exclude ".impl" --exclude ".worker-impl" || exit_code=1; \
	echo "\n--- Kit Markdown Check ---" && (cd packages/erk-kits/src/erk_kits/data/kits && uv run erk md check --exclude ".impl" --exclude ".worker-impl") || exit_code=1; \
	cd $(CURDIR); \
	echo "\n--- Docs Validate ---" && uv run erk docs validate || exit_code=1; \
	echo "\n--- Docs Sync Check ---" && uv run erk docs sync --check || exit_code=1; \
	echo "\n--- Pyright ---" && uv run pyright || exit_code=1; \
	echo "\n--- Kit Build ---" && $(MAKE) kit-build-autofix || exit_code=1; \
	echo "\n--- Unit Tests (erk) ---" && uv run pytest tests/unit/ tests/commands/ tests/core/ -n auto || exit_code=1; \
	echo "\n--- Tests (erk-dev) ---" && uv run pytest packages/erk-dev -n auto || exit_code=1; \
	echo "\n--- Kit Check ---" && uv run erk kit check || exit_code=1; \
	echo "\n--- Kit Build Check ---" && uv run erk dev kit-build --check || exit_code=1; \
	exit $$exit_code

# CI target: Run all tests (unit + integration) for comprehensive validation
all-ci:
	@echo "=== All CI ===" && \
	exit_code=0; \
	echo "\n--- Lint ---" && uv run ruff check || exit_code=1; \
	echo "\n--- Format Check ---" && uv run ruff format --check || exit_code=1; \
	echo "\n--- Prettier Check ---" && prettier --check '**/*.md' --ignore-path .gitignore || exit_code=1; \
	echo "\n--- Markdown Check ---" && uv run erk md check --check-links --exclude "packages/*/src/*/data/kits" --exclude ".impl" --exclude ".worker-impl" || exit_code=1; \
	echo "\n--- Kit Markdown Check ---" && (cd packages/erk-kits/src/erk_kits/data/kits && uv run erk md check --exclude ".impl" --exclude ".worker-impl") || exit_code=1; \
	cd $(CURDIR); \
	echo "\n--- Docs Validate ---" && uv run erk docs validate || exit_code=1; \
	echo "\n--- Docs Sync Check ---" && uv run erk docs sync --check || exit_code=1; \
	echo "\n--- Pyright ---" && uv run pyright || exit_code=1; \
	echo "\n--- Kit Build ---" && $(MAKE) kit-build-autofix || exit_code=1; \
	echo "\n--- Unit Tests (erk) ---" && uv run pytest tests/unit/ tests/commands/ tests/core/ -n auto || exit_code=1; \
	echo "\n--- Integration Tests (erk) ---" && uv run pytest tests/integration/ -n auto || exit_code=1; \
	echo "\n--- Tests (erk-dev) ---" && uv run pytest packages/erk-dev -n auto || exit_code=1; \
	echo "\n--- Kit Check ---" && uv run erk kit check || exit_code=1; \
	echo "\n--- Kit Build Check ---" && uv run erk dev kit-build --check || exit_code=1; \
	exit $$exit_code

# Clean build artifacts
clean:
	rm -rf dist/*.whl dist/*.tar.gz

# Build erk and erk-kits packages
build: clean
	uv build --package erk-kits -o dist
	uv build --package erk -o dist

# Reinstall erk and dot-agent tools in editable mode
reinstall-erk-tools:
	uv tool install --force -e .

# Publish packages to PyPI
# Use erk-dev publish-to-pypi command instead (recommended)
publish: build
	erk-dev publish-to-pypi

pull_master:
	git -C /Users/schrockn/code/erk pull origin master
