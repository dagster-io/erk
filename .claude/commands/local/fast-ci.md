---
description: Run fast CI checks iteratively (unit tests only)
---

You are an implementation finalizer for rapid development feedback. Your task is to run `make fast-ci` and iteratively fix any issues until all CI checks pass successfully.

## Your Mission

Run the fast CI pipeline (`make fast-ci`) from the repository root and automatically fix any failures. Keep iterating until all checks pass or you get stuck on an issue that requires human intervention.

**Fast CI vs All CI**: The `fast-ci` target runs unit tests only, providing rapid feedback for development iteration. Use `/all-ci` when you need comprehensive validation including integration tests.

## CI Pipeline (make fast-ci)

The `make fast-ci` target runs these checks in order:

1. **lint** - Ruff linting checks
2. **format-check** - Ruff code formatting checks
3. **prettier-check** - Markdown formatting checks
4. **md-check** - AGENTS.md standard compliance validation
5. **docs-validate** - Agent documentation frontmatter validation
6. **ty** - Type checking
7. **test** - Pytest unit tests only (fast feedback loop)

## Iteration Process

Load the `ci-iteration` skill for the iterative fix workflow.

## Fail-Fast Workflow

This command uses a two-phase approach to fail fast on linting and type checking issues:

1. **Phase 1 (Fail-Fast)**: Run `make lint ty` together. If EITHER fails, stop immediately to fix issues before proceeding to remaining checks.
2. **Phase 2 (Remaining Checks)**: Only after phase 1 passes, run remaining checks via `make fast-ci`.

This ensures that common issues (linting/formatting and type errors) are caught and fixed first, providing rapid feedback without waiting for slower test runs.

## Begin Now

Start by using the Task tool with the devrun agent to run the fail-fast phase (`make lint ty`) from the repository root. If that passes, proceed with the remaining checks (`make format-check prettier-check md-check docs-validate test`). Track your progress with TodoWrite and report your final status clearly.

**Remember**:

- NEVER run pytest/ty/ruff/prettier/make/gt directly via Bash
- Always use the Task tool with subagent_type: devrun
- Covered tools: pytest, ty, ruff, prettier, make, gt
- Always ensure make commands execute from the repository root directory
