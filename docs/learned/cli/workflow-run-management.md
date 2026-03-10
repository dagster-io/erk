---
title: Workflow Run Management Commands
read_when:
  - "canceling or retrying workflow runs"
  - "working with erk workflow run cancel or retry"
  - "managing GitHub Actions workflow runs"
tripwires: []
---

# Workflow Run Management Commands

## Overview

Commands for managing GitHub Actions workflow runs: cancel in-progress runs and retry failed/completed runs.

## Commands

### erk workflow run cancel \<run_id\>

Cancel an in-progress or queued workflow run.

```bash
erk workflow run cancel 12345678
```

### erk workflow run retry \<run_id\> [--failed]

Retry a completed workflow run.

```bash
erk workflow run retry 12345678
erk workflow run retry 12345678 --failed  # Only re-run failed jobs
```

- `--failed` flag: Only re-run failed jobs (not all jobs)

## Implementation

- Cancel: `src/erk/cli/commands/run/cancel_cmd.py`
- Retry: `src/erk/cli/commands/run/retry_cmd.py`
- Both delegate to GitHub gateway methods (`cancel_workflow_run`, `rerun_workflow_run`)
- Both require GitHub CLI authentication (`Ensure.gh_authenticated`)
