# Fix: Objective prose reconciliation reads metadata-only body instead of comment

## Context

When landing a PR linked to an objective, the `objective-update-with-landed-pr` command's Step 3 (prose reconciliation) is supposed to compare the objective's prose sections (Design Decisions, Implementation Context, etc.) against what the PR actually did, and update stale sections. However, it never finds any prose because:

1. Objective prose lives in the **first comment** (wrapped in `objective-body` metadata block)
2. The issue body contains **only metadata** (`objective-header` + `objective-roadmap`)
3. `objective-fetch-context` returns `objective.body` (metadata-only) with no reference to the comment
4. `update-objective-node --include-body` returns `updated_body` which is also the metadata-only issue body
5. The command's Step 3 reconciles against `updated_body` — finds no prose, skips

**Result:** Prose reconciliation silently no-ops on every objective update.

## Changes

### 1. Add `objective_content` field to `ObjectiveInfoDict`

**File:** `packages/erk-shared/src/erk_shared/objective_fetch_context_result.py`

Add an `objective_content` field (type `str | None`) to `ObjectiveInfoDict`. This holds the parsed prose from the first comment's `objective-body` block.

### 2. Fetch the first comment in `objective-fetch-context`

**File:** `src/erk/cli/commands/exec/scripts/objective_fetch_context.py`

After fetching the objective issue (line 170), use existing utilities to fetch the prose:

```python
from erk_shared.gateway.github.metadata.core import (
    extract_objective_header_comment_id,
    extract_objective_from_comment,
)
```

Flow:
1. `extract_objective_header_comment_id(objective.body)` → get comment ID
2. If comment ID exists: `issues.get_comment_by_id(repo_root, comment_id)` → get comment body
3. `extract_objective_from_comment(comment_body)` → extract prose markdown
4. Include the result as `objective_content` in the output dict

All three functions already exist and are production-tested. If any step fails (no comment ID, comment not found, no objective-body block), set `objective_content` to `None`.

**Key files with reusable functions:**
- `extract_objective_header_comment_id()` — `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py:749`
- `extract_objective_from_comment()` — `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py:765`
- `issues.get_comment_by_id()` — `packages/erk-shared/src/erk_shared/gateway/github/issues/abc.py` (ABC), `real.py:334` (impl)

### 3. Update command Step 3 to reconcile against `objective_content`

**File:** `.claude/commands/erk/objective-update-with-landed-pr.md`

Change Step 3 to read prose from `objective.objective_content` (the first comment's parsed content) instead of `updated_body` (the metadata-only issue body). The `updated_body` from Step 2 is still used for roadmap metadata but should not be the source of prose reconciliation.

Also update Step 5 to clarify: if prose reconciliation found stale sections, the agent updates the **first comment** (not the issue body) using the appropriate mechanism.

### 4. Update existing tests

**File:** `tests/unit/cli/commands/exec/scripts/test_objective_fetch_context.py`

Add test coverage for the new `objective_content` field:
- Test that when a comment ID exists and comment has objective-body content, it appears in output
- Test that when no comment ID exists, `objective_content` is `None`

## Verification

1. Run existing tests: `pytest tests/unit/cli/commands/exec/scripts/test_objective_fetch_context.py`
2. Run type checker on changed files
3. Manual test: `erk exec objective-fetch-context --pr <pr> --objective 7823` and verify `objective_content` contains the prose
