---
description: Run Python-only fast CI checks iteratively (lint, format, ty, unit tests)
---

You are an implementation finalizer for rapid Python-focused development feedback. Your task is to run `make py-fast-ci` and iteratively fix any issues until all CI checks pass successfully.

## Your Mission

Run the Python-only fast CI pipeline (`make py-fast-ci`) from the repository root and automatically fix any failures. Keep iterating until all checks pass or you get stuck on an issue that requires human intervention.

**py-fast-ci vs fast-ci**: The `py-fast-ci` target runs Python checks (lint, format, ty, pytest), skipping markdown and documentation checks. Use this when you're iterating on Python code and don't want to wait for prettier/markdown validation. Use `/fast-ci` when you need the full fast CI pipeline including all checks.

## CI Pipeline (make py-fast-ci)

The `make py-fast-ci` target runs these checks in order:

1. **lint** - Ruff linting checks
2. **format** - Python formatting check (ruff format --check)
3. **ty** - Type checking
4. **test-unit-erk** - Pytest unit tests for erk
5. **test-erk-dev** - Pytest tests for erk-dev

**Skipped** (compared to fast-ci):

- Prettier check (markdown formatting)
- Markdown check (AGENTS.md compliance)
- Docs validate/sync

## Iteration Process

Load the `ci-iteration` skill for the iterative fix workflow.

## Fail-Fast Workflow

This command uses a two-phase approach to fail fast on Python code quality issues:

1. **Phase 1 (Fail-Fast)**: Run `make lint format ty` together (ruff lint + ruff format + type checking). If ANY fails, stop immediately to fix issues before proceeding to test runs.
2. **Phase 2 (Test Runs)**: Only after phase 1 passes, run `make test-unit-erk test-erk-dev`.

This ensures that syntax/formatting and type errors are caught and fixed first, providing rapid feedback without waiting for test execution.

## Begin Now

Start by using the Task tool with the devrun agent to run the fail-fast phase (`make lint format ty`) from the repository root. If that passes, proceed with test targets (`make test-unit-erk test-erk-dev`). Track your progress with TodoWrite and report your final status clearly.

**Remember**:

- NEVER run pytest/ty/ruff/prettier/make/gt directly via Bash
- Always use the Task tool with subagent_type: devrun
- Covered tools: pytest, ty, ruff, prettier, make, gt
- Always ensure make commands execute from the repository root directory
