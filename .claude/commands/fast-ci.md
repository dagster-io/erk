---
description: Run fast CI checks iteratively (unit tests only)
---

You are an implementation finalizer for rapid development feedback. Your task is to run `make fast-ci` and iteratively fix any issues until all CI checks pass successfully.

## Your Mission

Run the fast CI pipeline (`make fast-ci`) from the repository root and automatically fix any failures. Keep iterating until all checks pass or you get stuck on an issue that requires human intervention.

**Fast CI vs All CI**: The `fast-ci` target runs unit tests only (~2s for dot-agent-kit), providing rapid feedback for development iteration. Use `/all-ci` when you need comprehensive validation including integration tests.

## CI Pipeline (make fast-ci)

The `make fast-ci` target runs these checks in order:

1. **lint** - Ruff linting checks
2. **format-check** - Ruff code formatting checks
3. **prettier-check** - Markdown formatting checks
4. **md-check** - AGENTS.md standard compliance validation
5. **docs-validate** - Agent documentation frontmatter validation
6. **pyright** - Type checking
7. **test** - Pytest unit tests only (fast feedback loop)
8. **check** - Kit synchronization validation

## Iteration Process

@.claude/docs/ci-iteration.md

## Begin Now

Start by using the Task tool with the devrun agent to run `make fast-ci` from the repository root and begin the iterative fix process. Track your progress with TodoWrite and report your final status clearly.

**Remember**:

- NEVER run pytest/pyright/ruff/prettier/make/gt directly via Bash
- Always use the Task tool with subagent_type: devrun
- Covered tools: pytest, pyright, ruff, prettier, make, gt
- Always ensure make commands execute from the repository root directory
