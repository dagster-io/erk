---
title: Autofix Job Needs
read_when:
  - "modifying the autofix job's needs list in ci.yml"
  - "adding a new CI job that might block autofix"
  - "understanding autofix dependency design"
tripwires:
  - action: "removing test jobs from autofix's needs list"
    warning: "Autofix depends on ALL validation jobs including unit-tests and integration-tests. It needs full failure context to attempt intelligent fixes. See the needs array in ci.yml."
---

# Autofix Job Needs

## Current Design

The autofix job depends on **all** validation jobs, including test jobs. This gives the autofix agent full failure context to attempt intelligent fixes.

<!-- Source: .github/workflows/ci.yml, autofix job needs array -->

See the `autofix` job's `needs` array in `.github/workflows/ci.yml` for the authoritative list:

- format, lint, fix-formatting, docs-check, ty, unit-tests, integration-tests

The job uses `always()` in its `if` condition, so it runs even when upstream jobs fail. The dependency list controls **ordering** (autofix waits for all jobs to finish) rather than **gating** (autofix still runs on failure).

## Why All Jobs Are Included

The autofix agent uses Claude Code with failure context from all jobs. Including test jobs in `needs` ensures:

1. All job results are available via `needs.<job>.result`
2. The agent sees both style failures AND test failures in one pass
3. Error messages from test jobs are collected and passed to Claude

The `always()` condition prevents the deadlock that would otherwise occur — autofix runs regardless of whether upstream jobs succeed or fail.

## Decision Table: Dependencies

| Job Type             | In needs? | Rationale                             |
| -------------------- | --------- | ------------------------------------- |
| format (ruff format) | Yes       | Failure context for auto-fix          |
| lint (ruff check)    | Yes       | Failure context for auto-fix          |
| fix-formatting       | Yes       | Must complete before autofix runs     |
| docs-check           | Yes       | Failure context for docs-sync         |
| ty (type check)      | Yes       | Failure context for type fixes        |
| unit-tests           | Yes       | Failure context for intelligent fixes |
| integration-tests    | Yes       | Failure context for intelligent fixes |

## Kill Switch

Autofix is currently disabled via a `false &&` guard in its `if` condition. When re-enabled, it will run after all validation jobs complete.

## Related Patterns

- [CI Iteration Pattern](ci-iteration.md) - Iterative fixing of CI failures
- [Workflow Gating Patterns](workflow-gating-patterns.md) - Conditional job execution strategies
