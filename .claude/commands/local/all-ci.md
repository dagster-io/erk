---
description: Run full CI checks iteratively (all tests including integration)
---

You are an implementation finalizer for comprehensive validation. Your task is to run `make all-ci` and iteratively fix any issues until all CI checks pass successfully.

## Your Mission

Run the full CI pipeline (`make all-ci`) from the repository root and automatically fix any failures. Keep iterating until all checks pass or you get stuck on an issue that requires human intervention.

**Fast CI vs All CI**: The `all-ci` target runs both unit and integration tests (~14s for dot-agent-kit), providing comprehensive validation before submitting code. Use `/fast-ci` for rapid development feedback with unit tests only.

## CI Pipeline (make all-ci)

The `make all-ci` target runs these checks in order:

1. **lint** - Ruff linting checks
2. **format-check** - Ruff code formatting checks
3. **prettier-check** - Markdown formatting checks
4. **md-check** - AGENTS.md standard compliance validation
5. **pyright** - Type checking
6. **test-all** - Pytest test suite (unit + integration tests)
7. **check** - Kit synchronization validation

## Iteration Process

@.claude/docs/ci-iteration.md

## Begin Now

Start by using the Task tool with the devrun agent to run `make all-ci` from the repository root and begin the iterative fix process. Track your progress with TodoWrite and report your final status clearly.

**Remember**:

- NEVER run pytest/pyright/ruff/prettier/make/gt directly via Bash
- Always use the Task tool with subagent_type: devrun
- Covered tools: pytest, pyright, ruff, prettier, make, gt
- Always ensure make commands execute from the repository root directory
