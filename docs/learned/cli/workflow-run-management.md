---
title: Workflow Run Management
read_when:
  - "cancelling a GitHub Actions workflow run"
  - "retrying a failed GitHub Actions workflow run"
  - "working with erk workflow run cancel or retry"
---

# Workflow Run Management

Erk provides CLI commands to manage GitHub Actions workflow runs directly.

## Commands

### `erk workflow run cancel <run_id>`

Cancel an in-progress or queued workflow run.

**Source**: `src/erk/cli/commands/run/cancel_cmd.py`

```bash
erk workflow run cancel 12345678
```

Uses `ctx.github.cancel_workflow_run()` to cancel the run. Requires `gh` authentication.

### `erk workflow run retry <run_id>`

Retry a completed workflow run.

**Source**: `src/erk/cli/commands/run/retry_cmd.py`

```bash
erk workflow run retry 12345678           # Retry all jobs
erk workflow run retry 12345678 --failed  # Retry only failed jobs
```

**Options**:
- `--failed` — Only re-run the jobs that failed in the previous run (faster, cheaper than full retry)

Uses `ctx.github.rerun_workflow_run()` with `failed_only` parameter.

## Run IDs

Run IDs are available from `erk workflow run list` in the `run-id` column.

## Command Hierarchy

These commands live under `erk workflow run` (not `erk run`) following the workflow namespace introduced in PR #8549 that moved `erk run` to `erk workflow run`.

## Related Documentation

- [Workflow Run List](workflow-run-list.md) — Finding run IDs and viewing run status
- [Workflow Commands](workflow-commands.md) — Launching workflows remotely via `erk launch`
