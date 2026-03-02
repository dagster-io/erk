---
title: Piped Output Flushing Pattern
read_when:
  - "debugging silent CLI commands in piped environments"
  - "adding progress messages to long-running commands"
tripwires:
  - action: "adding click.echo() without sys.stdout.flush() in pipeline commands"
    warning: "Python buffers stdout when piped. Without explicit flush, users see no output until command completes or buffer fills."
---

# Piped Output Flushing Pattern

## Problem

`erk pr submit` appeared to hang with no output when piped (e.g., captured by CI or automation). The command was running correctly but all output was buffered until completion.

## Root Cause

Python's stdout is line-buffered when connected to a TTY but fully buffered when piped. `click.echo()` inherits this behavior, so output only appears when the buffer fills or the process exits.

## Solution

Add `sys.stdout.flush()` after banner output and after each pipeline step:

```python
click.echo(click.style("Submitting PR...", bold=True))
click.echo("")
sys.stdout.flush()
```

## Progress Messages

Add dim-styled progress messages for phases that would otherwise appear silent:

- `"Resolving branch and plan context..."`
- `"Checking for existing PR..."`

These messages provide feedback even in non-TTY environments.

## Timeout Protection

External subprocess calls (`gt auth`, `gt branch info`) use 15-second timeouts with graceful degradation:

- `check_auth_status()` returns `(False, None, None)` on timeout
- `is_branch_tracked()` returns `False` on timeout

## Files

- `src/erk/cli/commands/pr/submit_cmd.py:171-173` - Banner flush
- `src/erk/cli/commands/pr/submit_pipeline.py` - Pipeline step flushes
- `packages/erk-shared/src/erk_shared/gateway/graphite/real.py` - Graphite gateway timeouts
