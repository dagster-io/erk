# Plan: Parallelize local CI — lint alongside tests

## Context

The `make all-ci`, `fast-ci`, and `py-fast-ci` targets run all checks sequentially. Linting (ruff, prettier, ty, markdown/docs checks) is I/O-heavy while pytest is CPU-heavy — they don't contend, so running them in parallel saves wall-clock time. The user wants this to "just work" with `make all-ci` (no special flags).

GitHub CI already parallelizes at the job level (separate jobs for lint, format, ty, tests). This change brings the same benefit to local runs.

## Approach

Use bash backgrounding within each Make target: start the lint group in a background subshell (output captured to a temp file), run tests in the foreground, then `wait` for lint and display its output.

- **Foreground (tests)**: Output streams in real-time so you see test progress
- **Background (lint)**: Output buffered to `/tmp/erk-ci-lint.out`, displayed after tests finish
- Lint is fast, so results are always ready by the time tests complete

Both groups preserve the existing continue-on-error behavior (`|| exit_code=1`).

## Changes

**File: `Makefile`** — modify 3 targets:

### `all-ci` (line 112)

```makefile
all-ci:
	@echo "=== All CI ===" && \
	exit_code=0; \
	( \
		lint_exit=0; \
		echo "--- Lint ---" && uv run ruff check || lint_exit=1; \
		echo "--- Format Check ---" && uv run ruff format --check || lint_exit=1; \
		echo "--- Prettier Check ---" && prettier --check '**/*.md' --ignore-path .gitignore || lint_exit=1; \
		echo "--- Markdown Check ---" && uv run erk md check || lint_exit=1; \
		echo "--- Docs Check ---" && uv run erk docs check || lint_exit=1; \
		echo "--- Exec Reference Check ---" && uv run erk-dev gen-exec-reference-docs --check || lint_exit=1; \
		echo "--- ty ---" && uv run ty check || lint_exit=1; \
		exit $$lint_exit \
	) > /tmp/erk-ci-lint.out 2>&1 & lint_pid=$$!; \
	echo "\n--- Unit Tests (erk) ---" && uv run pytest tests/unit/ tests/commands/ tests/core/ tests/real/ -n auto || exit_code=1; \
	echo "\n--- Integration Tests (erk) ---" && uv run pytest tests/integration/ -n auto || exit_code=1; \
	echo "\n--- Tests (erk-dev) ---" && uv run pytest packages/erk-dev -n auto || exit_code=1; \
	echo "\n--- Tests (erk-statusline) ---" && uv run pytest packages/erk-statusline -n auto || exit_code=1; \
	echo "\n--- Tests (erkbot) ---" && cd packages/erkbot && uv run pytest tests/ -x -q && cd ../.. || exit_code=1; \
	echo "\n--- Lint/Format Results ---"; \
	wait $$lint_pid || exit_code=1; \
	cat /tmp/erk-ci-lint.out; \
	exit $$exit_code
```

### `fast-ci` (line 96)

Same pattern, without integration tests and without docs check.

### `py-fast-ci` (line 83)

Same pattern, lint group is just: ruff check, ruff format --check, ty check (no prettier/markdown/docs).

## Verification

- `make fast-ci` — confirm lint output appears after test output, all checks still run
- `make all-ci` — same verification with integration tests
- Intentionally break a lint rule (e.g., unused import) and confirm it's reported
- Intentionally break a test and confirm it's reported
- Confirm both failures in the same run are both reported (continue-on-error works)
