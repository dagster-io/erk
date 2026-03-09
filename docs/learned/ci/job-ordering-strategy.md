---
title: CI Job Ordering Strategy
read_when:
  - "modifying CI job dependencies"
  - "adding new CI jobs"
  - "understanding fix-formatting gating"
  - "debugging why CI restarted after a push"
tripwires:
  - action: "adding a new format-sensitive CI job without including fix-formatting in its needs list"
    warning: "Format-sensitive jobs (format, docs-check) must depend on both check-submission and fix-formatting. Test jobs (lint, ty, unit-tests, integration-tests, erk-mcp-tests) run speculatively with only check-submission."
  - action: "adding code review execution to ci.yml"
    warning: "Keep shipped review behavior in code-reviews.yml. Repo-local ci.yml should only own formatting, validation, and CI summaries."
---

# CI Job Ordering Strategy

The repo-local CI workflow uses a two-track architecture: a gate job controls entry, then format-sensitive jobs wait for `fix-formatting` while test jobs run speculatively in parallel. Convention-based reviews run separately in `code-reviews.yml`.

<!-- Source: .github/workflows/ci.yml -->

## Two-Track Architecture

```
check-submission (gate)
    ├── fix-formatting ──→ format, docs-check  (wait for clean code)
    └── lint, ty, unit-tests, integration-tests, erk-mcp-tests  (speculative)
```

### Gate

**`check-submission`** runs first with no dependencies. It checks whether the PR is a draft or labeled `erk-plan-review`, and outputs a `skip` flag consumed by all downstream jobs. This prevents wasted compute on PRs that aren't ready for validation.

### Format Track (wait for fix-formatting)

**`fix-formatting`** depends only on `check-submission`. It runs ruff formatting, markdown fixes, and docs-sync automatically. If changes are needed, it commits and pushes, which triggers a workflow restart via `cancel-in-progress: true`.

**Format-sensitive jobs** depend on both `check-submission` AND `fix-formatting`, and check `pushed != 'true'`:

| Job          | Purpose                  |
| ------------ | ------------------------ |
| `format`     | ruff format --check      |
| `docs-check` | Documentation compliance |

These jobs would fail on unformatted code, so they must wait for `fix-formatting` to complete.

### Speculative Track (parallel with fix-formatting)

**Speculative jobs** depend only on `check-submission` and start immediately:

| Job                 | Purpose                                 |
| ------------------- | --------------------------------------- |
| `lint`              | ruff check                              |
| `ty`                | Type checking                           |
| `unit-tests`        | Unit tests (matrix: Python 3.11-3.14)   |
| `integration-tests` | Integration tests                       |
| `erk-mcp-tests`     | MCP package tests (`make test-erk-mcp`) |

These jobs are unaffected by formatting changes. If `fix-formatting` pushes an autofix commit, `cancel-in-progress: true` kills the old run and a fresh run starts with all jobs passing.

This saves 1-3 minutes of wall-clock time on every CI run where code is already formatted (the common case).

## Skip-on-Push Mechanism

When `fix-formatting` pushes an autofix commit, a new CI run is triggered with the corrected code. Format-sensitive jobs (`format`, `docs-check`) check `needs.fix-formatting.outputs.pushed != 'true'` and skip immediately rather than racing against the cancellation signal.

Speculative jobs don't check `pushed` — they rely on `cancel-in-progress: true` to kill the old run when the new run starts. This is safe because:

- `pushed=true` means a new CI run is incoming that will cancel this one
- The speculative jobs' results from the old run are discarded anyway

The workflow uses branch-level concurrency grouping with `cancel-in-progress: true` as the primary cancellation mechanism for speculative jobs.

## Completion Jobs

**`ci-summarize`** depends on all validation jobs and runs only on failure. It uses a lightweight model to summarize CI failures for developers.

## Related Documentation

- [Formatting Workflow](formatting-workflow.md) — Formatting tool decision tree
- [Workflow Gating Patterns](workflow-gating-patterns.md) — Gate job patterns
- [Convention-Based Code Reviews](convention-based-reviews.md) — Separate shipped review workflow architecture
