# Plan: Auto-Close Review PRs on Plan Close/Implement

## Goal

When a plan is implemented (landed) or explicitly closed, automatically close any associated PR plan review with a comment explaining why.

## Approach

Create a shared helper function `cleanup_review_pr` and call it from two trigger points:

1. `erk plan close` — before closing linked PRs
2. `erk land` execute path — after merge, alongside other plan cleanup

The helper is **fail-open**: if review PR cleanup fails, the main operation still succeeds (warnings are logged).

## Changes

### 1. New file: `src/erk/cli/commands/review_pr_cleanup.py`

Shared helper function:

```python
def cleanup_review_pr(
    ctx: ErkContext,
    *,
    repo_root: Path,
    issue_number: int,
    reason: str,
) -> int | None:
```

Logic:

1. LBYL: Check issue exists, has plan-header block, has non-null `review_pr`
2. Add comment to review PR: `"This review PR was automatically closed because {reason}."`
3. Close the review PR via `ctx.github.close_pr`
4. Clear `review_pr` metadata (archives to `last_review_pr`) via `clear_plan_header_review_pr`
5. Output success/warning messages
6. Return the review PR number if closed, None otherwise

Each step has independent error handling. If close fails, metadata is NOT cleared (preserves consistency). Uses `find_metadata_block` + `block.data.get("review_pr")` for LBYL.

### 2. Modify: `src/erk/cli/commands/plan/close_cmd.py`

In `close_plan()`, add review PR cleanup **before** `_close_linked_prs()`:

```python
from erk.cli.commands.review_pr_cleanup import cleanup_review_pr

# After fetching plan, before _close_linked_prs:
cleanup_review_pr(
    ctx,
    repo_root=repo_root,
    issue_number=number,
    reason=f"the plan (issue #{number}) was closed",
)
```

Note: `_close_linked_prs` may attempt to close the review PR again — this is harmless since it only closes OPEN PRs and the review PR will already be CLOSED.

### 3. Modify: `src/erk/cli/commands/land_cmd.py`

In `_execute_land()`, add review PR cleanup after step 2.75 (tripwire promotion), before step 3 (cleanup):

```python
from erk.cli.commands.review_pr_cleanup import cleanup_review_pr

# After line ~1694, before Step 3:
if plan_issue_number is not None:
    cleanup_review_pr(
        ctx,
        repo_root=main_repo_root,
        issue_number=plan_issue_number,
        reason=f"the plan (issue #{plan_issue_number}) was implemented and landed",
    )
```

### 4. Tests

**`tests/commands/plan/test_review_pr_cleanup.py`** — unit tests for the helper:

- `test_cleanup_review_pr_closes_and_comments()` — happy path: comment added, PR closed, metadata cleared
- `test_cleanup_review_pr_no_review_pr()` — review_pr is None → no-op
- `test_cleanup_review_pr_no_plan_header()` — no plan-header block → no-op
- `test_cleanup_review_pr_issue_not_found()` — issue doesn't exist → no-op
- `test_cleanup_review_pr_close_failure_preserves_metadata()` — close_pr fails → metadata NOT cleared

**Update `tests/commands/plan/test_close.py`** — add test:

- `test_close_plan_with_review_pr_adds_comment()` — plan has review_pr; verify comment added to review PR before closure

## Files to Modify

| File                                            | Action                                           |
| ----------------------------------------------- | ------------------------------------------------ |
| `src/erk/cli/commands/review_pr_cleanup.py`     | **Create** — shared helper                       |
| `src/erk/cli/commands/plan/close_cmd.py`        | **Modify** — add cleanup call                    |
| `src/erk/cli/commands/land_cmd.py`              | **Modify** — add cleanup call in `_execute_land` |
| `tests/commands/plan/test_review_pr_cleanup.py` | **Create** — helper unit tests                   |
| `tests/commands/plan/test_close.py`             | **Modify** — add review PR test                  |

## Design Decisions

- **No branch deletion**: Unlike `plan_review_complete`, this helper skips branch deletion to keep it lightweight and fail-open. Dead branches are cleaned up separately.
- **Comment before close**: Comment is added first so the review PR shows the reason even if viewed after closure.
- **Metadata cleared only on successful close**: Prevents inconsistent state where metadata says no review PR but the PR is still open.

## Verification

1. Run unit tests: `pytest tests/commands/plan/test_review_pr_cleanup.py`
2. Run close tests: `pytest tests/commands/plan/test_close.py`
3. Run land tests: `pytest tests/commands/land/`
4. Run full CI: `make fast-ci`
