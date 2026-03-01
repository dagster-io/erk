# Context

When landing a PR with `erk land`, the `_create_learn_pr_impl` function calls `generate_branch_slug` unconditionally — even when no sessions are discovered. `generate_branch_slug` spawns a nested `claude --print` subprocess to generate a branch name slug, which hangs (120s timeout) because it runs Claude-within-Claude.

The output shows "No sessions discovered for this plan" but then the process hangs indefinitely because the code continues to the `generate_branch_slug` LLM call on line 388.

When there are no sessions, a learn plan has minimal value (just PR metadata, no session content). The fix is to early-return after session discovery when no sessions are found.

# Fix

**File:** `src/erk/cli/commands/land_learn.py`

In `_create_learn_pr_impl`, add an early return after `_log_session_discovery` when `all_session_ids` is empty:

```python
# Log session discovery summary and collect XML files for embedding
xml_files = _log_session_discovery(ctx, sessions=sessions, all_session_ids=all_session_ids)

# Skip learn plan creation if no sessions were discovered — nothing meaningful to capture
if not all_session_ids:
    return
```

This goes at line ~372, right after the `_log_session_discovery` call and before building the plan body.

# Verification

1. Run `erk land -f -d` on a PR where no sessions are associated — it should complete quickly after "No sessions discovered for this plan" without hanging
2. Run `erk land -f -d` on a PR with sessions — learn plan should still be created as before
3. Confirm no test regressions with `make fast-ci`
