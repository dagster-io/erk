---
title: CI Job Ordering Strategy
read_when:
  - "modifying CI job dependencies"
  - "adding new CI jobs"
  - "understanding fix-formatting gating"
  - "debugging why CI restarted after a push"
tripwires:
  - action: "adding a new CI job without including fix-formatting in its needs list"
    warning: "All validation jobs must depend on both check-submission and fix-formatting. Without fix-formatting, the job may run against unformatted code and fail unnecessarily."
  - action: "adding test jobs to autofix's needs list"
    warning: "Autofix only depends on auto-fixable jobs (format, lint, docs-check, ty). Adding test jobs creates a deadlock. See autofix-job-needs.md."
---

# CI Job Ordering Strategy

The CI workflow uses a three-tier architecture where a gate job controls entry, an auto-fix job runs formatting corrections, and seven parallel validation jobs run against the cleaned state.

<!-- Source: .github/workflows/ci.yml -->

## Three-Tier Architecture

```
Tier 1: check-submission (gate)
    │
Tier 2: fix-formatting (auto-fix, independent of parallel jobs)
    │
Tier 3: ┌──────┬──────┬───────────┬────┬────────────┬─────────────┬──────────────┐
         format  lint  docs-check  ty  unit-tests  integration  erkbot-tests
```

### Tier 1: Gate

**`check-submission`** runs first with no dependencies. It checks whether the PR is a draft or labeled `erk-plan-review`, and outputs a `skip` flag consumed by all downstream jobs. This prevents wasted compute on PRs that aren't ready for validation.

### Tier 2: Auto-Fix

**`fix-formatting`** depends only on `check-submission` — it does NOT wait for the parallel validation jobs. It runs ruff formatting, markdown fixes, and docs-sync automatically. If changes are needed, it commits and pushes, which triggers a workflow restart via `cancel-in-progress: true`.

This ordering is intentional: fix-formatting runs early to clean up code before validation jobs evaluate it.

### Tier 3: Parallel Validation

Seven jobs run in parallel, all depending on both `check-submission` AND `fix-formatting`:

| Job                 | Purpose                               |
| ------------------- | ------------------------------------- |
| `format`            | ruff format --check                   |
| `lint`              | ruff check                            |
| `docs-check`        | Documentation compliance              |
| `ty`                | Type checking                         |
| `unit-tests`        | Unit tests (matrix: Python 3.11-3.14) |
| `integration-tests` | Integration tests                     |
| `erkbot-tests`      | Erkbot-specific tests                 |

## Cancellation Mechanism

The workflow uses branch-level concurrency grouping with `cancel-in-progress: true`:

<!-- Source: .github/workflows/ci.yml:15-17 -->

The `concurrency` block groups runs by branch ref and cancels in-progress runs when a new push arrives. When `fix-formatting` pushes a commit, a new workflow run starts and the in-progress run is cancelled. This means validation jobs always run against formatted code, at the cost of ~2 minutes for the restart cycle.

## Completion Jobs

**`ci-summarize`** depends on all validation jobs and runs only on failure. It uses a lightweight model to summarize CI failures for developers.

**`autofix`** depends on format, lint, fix-formatting, docs-check, and ty (auto-fixable jobs only). It deliberately excludes test jobs to prevent deadlock. Currently disabled via kill-switch (`false &&` guard).

## Related Documentation

- [Autofix Job Dependencies](autofix-job-needs.md) — Why autofix excludes test jobs
- [Formatting Workflow](formatting-workflow.md) — Formatting tool decision tree
- [Workflow Gating Patterns](workflow-gating-patterns.md) — Gate job patterns
