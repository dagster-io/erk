# Plan: Improve one-shot plan issue titles

## Context

One-shot plan issues currently get titled `[erk-plan] _Skeleton: plan content will be populated by one-shot workflow._` because `create_plan_issue` is called with `title=None`, causing it to extract the title from the skeleton body content (which has no H1/H2, so it falls back to the first line).

The PR title already uses `One-shot: {instruction}` format (line 119). The plan issue title should match.

## Changes

### 1. Pass explicit title to `create_plan_issue` (`src/erk/cli/commands/one_shot_dispatch.py`)

At line 152, change `title=None` to pass a truncated instruction as the title:

```python
skeleton_result = create_plan_issue(
    ...
    title=f"One-shot: {params.instruction[:max_title_len]}{suffix}",
    ...
)
```

This reuses the existing `max_title_len` and `suffix` variables from lines 117-118 (already computed for the PR title).

Result: `[erk-plan] One-shot: add user authentication`

### 2. Update test assertion (`tests/commands/one_shot/test_one_shot_dispatch.py`)

Line 223: Change `assert "Skeleton" in comment_body` to `assert "One-shot" in comment_body` (or check for the instruction text, since "Skeleton" will no longer appear).

Actually — the comment body still contains the skeleton content. Only the title changes. Let me re-check: the `comment_body` is the plan content passed to the first comment. The skeleton text is still in the body. So we should also update the body text to remove "Skeleton" language.

### 2b. Update skeleton body content

Change the body from:
```
_Skeleton: plan content will be populated by one-shot workflow._
```
to:
```
_One-shot: plan content will be populated by one-shot workflow._
```

### 3. Update test assertion

Update the test to assert `"One-shot"` instead of `"Skeleton"` in the comment body.

## Files to modify

- `src/erk/cli/commands/one_shot_dispatch.py` (lines 148-156)
- `tests/commands/one_shot/test_one_shot_dispatch.py` (line 223)

## Verification

- Run: `uv run pytest tests/commands/one_shot/test_one_shot_dispatch.py`
- Verify the test passes with updated assertions