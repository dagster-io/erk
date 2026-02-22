# Fix: ci-update-pr-body loses plan-header metadata on draft PR plans

## Context

When a draft-PR plan goes through remote implementation, `ci-update-pr-body` rewrites the PR body but **drops the plan-header metadata block**. This means:
- `last_dispatched_node_id` can never be written by subsequent workflows (fix-conflicts, address)
- The dashboard shows no `run_url` for the plan
- The `land` command is unavailable (it requires `run_url is not None`)

**Root cause:** `ci-update-pr-body` detects draft-PR plans by checking `.impl/plan-ref.json` on disk (line 323-326). In CI, this file may not survive the cleanup steps between implementation and the PR body update. When `is_draft_pr` is `False`, the code takes the issue-based path which builds a plain body without preserving the metadata prefix.

**Fix:** Add fallback detection from the PR body itself. If the fetched PR body contains a `plan-header` metadata block, it's a draft PR plan regardless of `.impl/plan-ref.json`.

## Changes

### 1. `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py`

**Add import:**
```python
from erk_shared.gateway.github.metadata.core import find_metadata_block
```

**Add fallback detection in `_update_pr_body_impl`** (around line 257, before the `if is_draft_pr:` block):

```python
# Fallback: detect draft-PR plan from PR body metadata block
# .impl/plan-ref.json may not survive CI cleanup steps
if not is_draft_pr and find_metadata_block(pr_result.body, "plan-header") is not None:
    is_draft_pr = True
```

This is a 2-line logic change + 1 import.

### 2. Test: `tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py`

Add a test case that verifies: when `is_draft_pr=False` but the PR body contains a `plan-header` metadata block, the code still preserves the metadata prefix and original plan section.

## Verification

1. Run existing tests for `ci_update_pr_body` to ensure no regressions
2. Run the new test to verify fallback detection works
3. Run `ruff check` and `ty check` on modified files
