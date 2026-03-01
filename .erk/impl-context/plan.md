# Plan: Skip Learn Plan Creation When No Session Material Found

## Context

When `erk land` runs, it creates a learn plan draft PR to capture implementation insights from Claude Code sessions. However, if a plan had zero tracked sessions (as in PR #8566), `_create_learn_pr_impl()` still creates a learn plan draft PR containing only `plan.md` and `ref.json` — no session XML files. This creates an empty/low-value learn plan that the downstream CI (`/erk:learn`) cannot meaningfully analyze.

The fix: if no session XML files were found during preprocessing, skip creating the learn plan entirely and notify the user with a clear message explaining why.

## Fix Location

**File:** `src/erk/cli/commands/land_learn.py`

**Function:** `_create_learn_pr_impl()`, after line 371 where `xml_files` is computed.

## Implementation

After this existing line:
```python
xml_files = _log_session_discovery(ctx, sessions=sessions, all_session_ids=all_session_ids)
```

Add an early-return guard:
```python
if not xml_files:
    user_output(
        click.style("ℹ", fg="blue")
        + f" Skipping learn plan for #{plan_id}: no session material found"
        + (" (no sessions were tracked for this plan)" if not all_session_ids else " (sessions found but no XML could be extracted)")
    )
    return
```

This handles two sub-cases:
- `all_session_ids` is empty → no sessions were tracked at all
- `all_session_ids` is non-empty but `xml_files` is empty → sessions exist but preprocessing failed

## Critical Files

- `src/erk/cli/commands/land_learn.py` — the only file to modify
  - `_create_learn_pr_impl()` at line 345
  - The guard is inserted after line 371

## Verification

1. Run `erk land` on a plan with zero sessions (e.g., a changelog-only PR)
2. Confirm the output shows the "Skipping learn plan" message instead of creating a draft PR
3. Confirm no new draft PR appears in the GitHub issue tracker
4. Confirm `erk land` exits cleanly (no error)

For a plan with sessions, confirm learn plan creation still works normally.
