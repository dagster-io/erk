---
title: CI Merge Gate Jobs
read_when:
  - "adding new CI jobs to ci.yml"
  - "understanding which jobs block merging"
  - "working with the ci-summarize job"
  - "understanding check-submission and fix-formatting interactions"
tripwires:
  - action: "adding a new CI job without checking if it should feed into ci-summarize"
    warning: "Jobs that can fail and block merge should be added to ci-summarize needs list. See merge-gate-jobs.md."
---

# CI Merge Gate Jobs

`.github/workflows/ci.yml` orchestrates parallel CI jobs. Several jobs gate merging; others are advisory or auto-fix.

## Key Jobs and Interactions

### `check-submission`

- Runs on all non-draft PRs
- Checks for `.erk/impl-context/` staging folder
- Output: `skip` — if `true`, most downstream jobs skip (plan branches not subject to normal CI)

### `no-impl-context`

- Validates `.erk/impl-context/` is NOT in the tree (must be cleaned up before merge)
- Runs independently of `check-submission`

### `fix-formatting`

- Runs `make docs-fix`, `ruff format`, and Prettier on `**/*.md`
- **Auto-commits** formatting fixes on non-fork PRs (outputs `pushed: true`)
- When `pushed == 'true'`: downstream format/docs-check jobs skip (new CI run triggered)
- Requires `ERK_QUEUE_GH_PAT` secret for push access

### `format`

- Needs: `check-submission`, `fix-formatting`
- Skips if `fix-formatting` auto-committed changes
- Runs `make format-check`

### `lint`

- Needs: `check-submission`
- Runs `make lint` (ruff)

### `docs-check`

- Needs: `check-submission`, `fix-formatting`
- Skips if `fix-formatting` auto-committed changes
- Runs `make md-check` and `make docs-check`

### `ty`

- Needs: `check-submission`
- Runs `make ty` (type checking)

### `unit-tests`

- Needs: `check-submission`
- Matrix: Python 3.11, 3.12, 3.13, 3.14 (fail-fast: false)
- Runs `make test`

### `integration-tests`

- Needs: `check-submission`
- Runs `make test-integration`

### `erk-mcp-tests`

- Needs: `check-submission`
- Runs `make test-erk-mcp`

## `ci-summarize` (AI Failure Summarization)

<!-- Source: .github/workflows/ci.yml:196-220 -->

When any of the core jobs fail on a non-draft PR, the `ci-summarize` job runs a Claude-based failure summarizer. See the ci-summarize job in `.github/workflows/ci.yml`.

Disabled via `CLAUDE_ENABLED=false` repository variable.

## Skip Condition

Jobs skip when `needs.check-submission.outputs.skip == 'true'` — set for plan implementation PRs that have `.erk/impl-context/` present (plan branches use a different CI flow).

## Source

`.github/workflows/ci.yml:1-220`
