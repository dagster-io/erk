# Speculative Test Execution in CI

## Context

Currently all 7 validation jobs wait for `fix-formatting` to complete before starting (~1-3 min). Most test jobs (ty, unit-tests, integration-tests, erk-mcp-tests, lint) are unaffected by formatting changes, so they waste time waiting. By running them speculatively in parallel with `fix-formatting`, we save 1-3 minutes of wall-clock time on every CI run where code is already formatted (the common case). If fix-formatting pushes changes, `cancel-in-progress: true` already cancels the old run and starts a fresh one.

## Design: Two-Track Architecture

```
check-submission (gate)
    ├── fix-formatting ──→ format, docs-check  (wait for clean code)
    └── lint, ty, unit-tests, integration-tests, erk-mcp-tests  (speculative)
```

**Format-sensitive jobs** (`format`, `docs-check`): Keep depending on `fix-formatting` — they'd fail on unformatted code.

**Speculative jobs** (`lint`, `ty`, `unit-tests`, `integration-tests`, `erk-mcp-tests`): Depend only on `check-submission`. Start immediately. If fix-formatting pushes, `cancel-in-progress` kills the old run and a new run starts with clean code.

## Changes

### 1. `.github/workflows/ci.yml`

For each speculative job (`lint`, `ty`, `unit-tests`, `integration-tests`, `erk-mcp-tests`):
- Change `needs: [check-submission, fix-formatting]` → `needs: [check-submission]`
- Remove `needs.fix-formatting.outputs.pushed != 'true'` from the `if:` condition

Keep `format` and `docs-check` unchanged (still depend on `fix-formatting` + check `pushed`).

Keep `ci-summarize` unchanged (still depends on all jobs including `fix-formatting`).

### 2. `docs/learned/ci/job-ordering-strategy.md`

Update three-tier diagram to show two-track architecture. Update the tripwire from "All validation jobs must depend on fix-formatting" to "Only format-sensitive jobs (format, docs-check) depend on fix-formatting; test jobs run speculatively."

### 3. Other docs (minor)

- `docs/learned/ci/workflow-gating-patterns.md` — update "pushed" output section
- `docs/learned/ci/formatting-workflow.md` — update integration points
- Run `erk docs sync` to regenerate tripwire indexes

## Verification

1. Push a branch with **clean formatting** → all jobs (speculative + format-sensitive) should run and pass in parallel
2. Push a branch with **dirty formatting** → fix-formatting pushes, speculative jobs get cancelled, new run starts with all jobs passing
3. Confirm `ci-summarize` still triggers correctly on failures
