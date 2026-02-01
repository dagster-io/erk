# Fix: `gh codespace start` does not exist

## Problem

`RealCodespace.start_codespace()` calls `gh codespace start -c {gh_name}`, but `gh codespace start` is not a valid subcommand. The `-c` flag also doesn't apply here (it's a `gh codespace ssh` flag).

## Fix

Replace the CLI call with the GitHub REST API equivalent using `gh api`:

**File:** `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` (line 28)

Change:
```python
cmd=["gh", "codespace", "start", "-c", gh_name],
```
To:
```python
cmd=["gh", "api", "--method", "POST", f"/user/codespaces/{gh_name}/start"],
```

This is a one-line change. The REST API endpoint `POST /user/codespaces/{name}/start` is the correct way to start a codespace and was confirmed working during investigation.

## Verification

1. Run existing codespace gateway tests via devrun agent
2. Run `erk codespace run objective next-plan 6423` to confirm the end-to-end flow works