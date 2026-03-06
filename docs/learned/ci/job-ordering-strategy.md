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
  - action: "adding code review execution to ci.yml"
    warning: "Keep shipped review behavior in code-reviews.yml. Repo-local ci.yml should only own formatting, validation, and CI summaries."
---

# CI Job Ordering Strategy

The repo-local CI workflow uses a three-tier architecture: a gate job controls entry, `fix-formatting` is the single mutating boundary, and seven validation jobs run against the cleaned state. Convention-based reviews run separately in `code-reviews.yml`.

<!-- Source: .github/workflows/ci.yml -->

## Three-Tier Architecture

```
Tier 1: check-submission (gate)
    │
Tier 2: fix-formatting (auto-fix, independent of parallel jobs)
    │
Tier 3: ┌──────┬──────┬───────────┬────┬────────────┬─────────────┬──────────────┐
         format  lint  docs-check  ty  unit-tests  integration  erk-mcp-tests
```

### Tier 1: Gate

**`check-submission`** runs first with no dependencies. It checks whether the PR is a draft or labeled `erk-plan-review`, and outputs a `skip` flag consumed by all downstream jobs. This prevents wasted compute on PRs that aren't ready for validation.

### Tier 2: Auto-Fix

**`fix-formatting`** depends only on `check-submission` — it does NOT wait for the parallel validation jobs. It runs ruff formatting, markdown fixes, and docs-sync automatically. If changes are needed, it commits and pushes, which triggers a workflow restart via `cancel-in-progress: true`.

This ordering is intentional: fix-formatting runs early to clean up code before validation jobs evaluate it.

### Tier 3: Parallel Validation

Seven jobs run in parallel, all depending on both `check-submission` AND `fix-formatting`:

| Job                 | Purpose                                 |
| ------------------- | --------------------------------------- |
| `format`            | ruff format --check                     |
| `lint`              | ruff check                              |
| `docs-check`        | Documentation compliance                |
| `ty`                | Type checking                           |
| `unit-tests`        | Unit tests (matrix: Python 3.11-3.14)   |
| `integration-tests` | Integration tests                       |
| `erk-mcp-tests`     | MCP package tests (`make test-erk-mcp`) |

## Skip-on-Push Mechanism

When `fix-formatting` pushes an autofix commit, a new CI run is triggered with the corrected code. To prevent tier 3 jobs from running against the old (unformatted) code during the race window before cancellation arrives, `fix-formatting` exposes a `pushed` output:

- `pushed=true` — autofix commit was pushed, new CI run incoming
- `pushed=false` — no changes needed (or error exit on master/fork)

All tier 3 jobs include `&& needs.fix-formatting.outputs.pushed != 'true'` in their `if:` condition. When `pushed` is `true`, these jobs skip immediately rather than racing against the cancellation signal.

The workflow also uses branch-level concurrency grouping with `cancel-in-progress: true` as a secondary mechanism — when the new run starts from the autofix push, it cancels any remaining jobs from the old run.

## Completion Jobs

**`ci-summarize`** depends on all validation jobs and runs only on failure. It uses a lightweight model to summarize CI failures for developers.

## Related Documentation

- [Formatting Workflow](formatting-workflow.md) — Formatting tool decision tree
- [Workflow Gating Patterns](workflow-gating-patterns.md) — Gate job patterns
- [Convention-Based Code Reviews](convention-based-reviews.md) — Separate shipped review workflow architecture
