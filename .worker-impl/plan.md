# Plan: Run All CI Phases Even on Failure

## Goal
Modify `fast-ci` and `all-ci` Make targets to run all test phases even when earlier phases fail, providing complete context for debugging and better CI reporting.

## Current State
```makefile
fast-ci: lint format-check prettier-check md-check pyright test check
all-ci: lint format-check prettier-check md-check pyright test-all check
```

These use Make's dependency syntax which stops at first failure.

## Solution
Rewrite both targets as shell scripts that:
1. Initialize an exit code accumulator
2. Run each phase, OR-ing failures into the accumulator
3. Print a summary of which phases passed/failed
4. Return non-zero if any phase failed

## Implementation

### Modified `fast-ci` target:
```makefile
fast-ci:
	@echo "=== Fast CI ===" && \
	exit_code=0; \
	echo "\n--- Lint ---" && uv run ruff check || exit_code=1; \
	echo "\n--- Format Check ---" && uv run ruff format --check || exit_code=1; \
	echo "\n--- Prettier Check ---" && prettier --check '**/*.md' --ignore-path .gitignore || exit_code=1; \
	echo "\n--- Markdown Check ---" && uv run dot-agent md check --check-links --exclude "packages/*/src/*/data/kits" || exit_code=1; \
	echo "\n--- Pyright ---" && uv run pyright || exit_code=1; \
	echo "\n--- Unit Tests ---" && uv run pytest tests/unit/ tests/commands/ tests/core/ -n auto || exit_code=1; \
	uv run pytest packages/erk-dev -n auto || exit_code=1; \
	cd packages/dot-agent-kit && uv run pytest tests/unit/ -n auto || exit_code=1; \
	cd $(CURDIR); \
	echo "\n--- Dot-Agent Check ---" && uv run dot-agent check || exit_code=1; \
	exit $$exit_code
```

### Modified `all-ci` target:
```makefile
all-ci:
	@echo "=== All CI ===" && \
	exit_code=0; \
	echo "\n--- Lint ---" && uv run ruff check || exit_code=1; \
	echo "\n--- Format Check ---" && uv run ruff format --check || exit_code=1; \
	echo "\n--- Prettier Check ---" && prettier --check '**/*.md' --ignore-path .gitignore || exit_code=1; \
	echo "\n--- Markdown Check ---" && uv run dot-agent md check --check-links --exclude "packages/*/src/*/data/kits" || exit_code=1; \
	echo "\n--- Pyright ---" && uv run pyright || exit_code=1; \
	echo "\n--- Unit Tests (erk) ---" && uv run pytest tests/unit/ tests/commands/ tests/core/ -n auto || exit_code=1; \
	echo "\n--- Integration Tests (erk) ---" && uv run pytest tests/integration/ -n auto || exit_code=1; \
	echo "\n--- Tests (erk-dev) ---" && uv run pytest packages/erk-dev -n auto || exit_code=1; \
	echo "\n--- Unit Tests (dot-agent-kit) ---" && (cd packages/dot-agent-kit && uv run pytest tests/unit/ -n auto) || exit_code=1; \
	echo "\n--- Integration Tests (dot-agent-kit) ---" && (cd packages/dot-agent-kit && uv run pytest tests/integration/ -n auto) || exit_code=1; \
	echo "\n--- Dot-Agent Check ---" && uv run dot-agent check || exit_code=1; \
	exit $$exit_code
```

## Key Changes
1. **Exit code tracking**: `exit_code=0` starts clean, `|| exit_code=1` captures failures
2. **Phase headers**: Echo statements before each phase for clear output
3. **Inline commands**: Expand the Make target dependencies into explicit commands
4. **Subshell for cd**: Use `(cd ... && ...)` to avoid working directory issues
5. **Final exit**: `exit $$exit_code` returns failure if any phase failed

## Files to Modify
- `Makefile` - lines 82-86

## Testing
After implementation, verify by:
1. Intentionally breaking one phase (e.g., add a lint error)
2. Run `make fast-ci`
3. Confirm all phases run and final exit code is non-zero