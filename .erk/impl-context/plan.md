# Fix: "(No plan content found)" for PR-only plans

## Context

Plan #8198 shows "(No plan content found)" in the TUI. The root cause: `fetch_plan_content()` has a code path for issue-based plans that fetches content from a GitHub comment via `plan_comment_id`. When a PR body happens to contain a `plan-header` metadata block (but no `plan_comment_id`), the method returns `None` instead of showing the content.

Since erk now only supports PR-based plans, the issue-based comment-fetching path is dead code.

## Change

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` (lines 363-401)

Simplify `fetch_plan_content` to always return `plan_body` directly — no metadata block inspection, no comment fetching. For PRs, `plan_body` is already the extracted content from `PlannedPRPlanListService`.

```python
# Before (broken for PRs with metadata in body):
def fetch_plan_content(self, plan_id: int, plan_body: str) -> str | None:
    block = find_metadata_block(plan_body, "plan-header")
    if block is None:
        return plan_body if plan_body.strip() else None
    comment_id = block.data.get(PLAN_COMMENT_ID)
    if not isinstance(comment_id, int):
        return None  # ← BUG: returns None for PRs with metadata
    # ... fetch comment via HTTP ...

# After (PR-only):
def fetch_plan_content(self, plan_id: int, plan_body: str) -> str | None:
    return plan_body if plan_body.strip() else None
```

Update docstring to reflect PR-only behavior. Remove now-unused imports if any.

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py`

Update the ABC docstring for `fetch_plan_content` to reflect PR-only semantics.

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`

Verify fake implementation is already consistent (likely already just returns stored content).

**File:** `tests/tui/data/test_fetch_plan_content.py`

- Remove/update tests for issue-based comment fetching path
- Add test: plan_body with embedded plan-header but no comment_id returns content
- Keep test: empty plan_body returns None

## Verification

- `uv run pytest tests/tui/data/test_fetch_plan_content.py`
- Verify plan #8198 displays content in the TUI
