# Add [erk-plan] Prefix to All Plan Creation Pathways

## Context

Plan issues and PRs should always have a `[erk-plan]` (or `[erk-learn]`) prefix in their title for visibility in GitHub. The canonical issue-based pathway in `create_plan_issue()` correctly adds the prefix, but two creation pathways are broken:

1. **`create_plan_from_context.py`**: Adds `[erk-plan]` as a **suffix** (`"title [erk-plan]"`) instead of a prefix. This is an older, legacy exec script.
2. **Draft PR backend (`_save_as_draft_pr` in `plan_save.py`)**: Passes the raw extracted title to `DraftPRPlanBackend.create_plan()` with no prefix at all.

## Files to Modify

### Fix 1: `create_plan_from_context.py`

**File:** `src/erk/cli/commands/exec/scripts/create_plan_from_context.py`

**Line 81 — change suffix to prefix:**

```python
# BEFORE (wrong: suffix)
issue_title = f"{title} [erk-plan]"

# AFTER (correct: prefix)
issue_title = f"[erk-plan] {title}"
```

Note: This script always creates standard (non-learn) plans, so `[erk-plan]` prefix is always correct here.

### Fix 2: `plan_save.py` — draft PR backend

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py`

In `_save_as_draft_pr()`, after the `labels` list is built (lines 194-196) and before `backend.create_plan()` is called (line 200), use `get_title_tag_from_labels()` to compute the correct prefix and apply it:

```python
# Import at top of file (add to existing imports from erk_shared.plan_utils):
from erk_shared.plan_utils import get_title_tag_from_labels

# In _save_as_draft_pr(), after labels are built:
labels = ["erk-plan"]
if plan_type == "learn":
    labels.append("erk-learn")

title_tag = get_title_tag_from_labels(labels)
prefixed_title = f"{title_tag} {title}"

# Then pass prefixed_title instead of title to backend.create_plan():
result = backend.create_plan(
    repo_root=repo_root,
    title=prefixed_title,   # was: title
    content=plan_content,
    labels=tuple(labels),
    metadata=metadata,
)
```

Also update the display/JSON output to use `prefixed_title` instead of `title` where the title is echoed back, so the output reflects the actual PR title.

## Verification

1. Run existing tests: `make fast-ci` — should pass
2. Manual smoke test with draft PR backend: save a plan and confirm the created PR title has `[erk-plan]` prefix
3. Manual smoke test with `create-plan-from-context`: pipe a plan to the exec script and confirm the issue title has `[erk-plan]` prefix (not suffix)
4. Check the tests for `create_plan_from_context` and `plan_save` in `tests/unit/cli/commands/exec/scripts/` and update any that assert the old suffix format
