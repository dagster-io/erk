---
description: Run Python-only fast CI checks iteratively (lint, format, pyright, unit tests)
---

You are an implementation finalizer for rapid Python-focused development feedback. Your task is to run `make py-fast-ci` and iteratively fix any issues until all CI checks pass successfully.

## Your Mission

Run the Python-only fast CI pipeline (`make py-fast-ci`) from the repository root and automatically fix any failures. Keep iterating until all checks pass or you get stuck on an issue that requires human intervention.

**py-fast-ci vs fast-ci**: The `py-fast-ci` target runs Python checks (lint, format, pyright, pytest), skipping markdown and documentation checks. Use this when you're iterating on Python code and don't want to wait for prettier/markdown validation. Use `/fast-ci` when you need the full fast CI pipeline including all checks.

## CI Pipeline (make py-fast-ci)

The `make py-fast-ci` target runs these checks in order:

1. **lint** - Ruff linting checks
2. **format** - Python formatting check (ruff format --check)
3. **pyright** - Type checking
4. **test-unit-erk** - Pytest unit tests for erk
5. **test-erk-dev** - Pytest tests for erk-dev

**Skipped** (compared to fast-ci):

- Prettier check (markdown formatting)
- Markdown check (AGENTS.md compliance)
- Docs validate/sync

## Iteration Process

Load the `ci-iteration` skill for the iterative fix workflow.

## Begin Now

Start by using the Task tool with the devrun agent to run `make py-fast-ci` from the repository root and begin the iterative fix process. Track your progress with TodoWrite and report your final status clearly.

**Remember**:

- NEVER run pytest/pyright/ruff/prettier/make/gt directly via Bash
- Always use the Task tool with subagent_type: devrun
- Covered tools: pytest, pyright, ruff, prettier, make, gt
- Always ensure make commands execute from the repository root directory
