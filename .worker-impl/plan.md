# Plan: Improve Plan PR Body Visual Formatting

## Context

Plan PRs (draft PRs that store plans) have a body with three sections:
1. `plan-header` metadata block (collapsed `<details>`)
2. `---` divider
3. `original-plan` content (collapsed `<details>`)
4. `---` divider (from footer)
5. Checkout footer

The `original-plan` summary label renders as plain text. It should use a monospace/code font (`<code>` tag) to match the `plan-header` block's existing `<code>` styling. Additionally, the divider below the original-plan section should cleanly match the one above it.

## Changes

### 1. Add `<code>` tag to `original-plan` summary

**File**: `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py`

Change `DETAILS_OPEN` constant (line 87):
```python
# Before
DETAILS_OPEN = "<details>\n<summary>original-plan</summary>\n\n"

# After
DETAILS_OPEN = "<details>\n<summary><code>original-plan</code></summary>\n\n"
```

### 2. Add backward-compatible extraction

**File**: `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py`

Add a legacy constant and update `extract_plan_content` to try the new format first, then fall back to old format:

```python
_LEGACY_DETAILS_OPEN = "<details>\n<summary>original-plan</summary>\n\n"
```

Update `extract_plan_content` to try `DETAILS_OPEN` first (new `<code>` format), then `_LEGACY_DETAILS_OPEN` (old plain text format), then the flat backward-compat fallback.

### 3. Update docstrings

Update the module docstring's body format examples (lines 38-43, 57-63) to reflect `<code>` tags in summary.

### 4. Update tests

**File**: `tests/unit/plan_store/test_draft_pr_lifecycle.py`

- Existing tests use `DETAILS_OPEN` constant so they'll pass automatically with the new value
- Add a test for backward compat: `test_extract_plan_content_from_legacy_details_format` that manually constructs a body with the old `<summary>original-plan</summary>` (no `<code>`) and verifies extraction still works

**File**: `tests/test_utils/plan_helpers.py` (line 117)

Uses `DETAILS_OPEN` constant directly, so it picks up the new value automatically.

## Files Modified

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py` | `<code>` tag in DETAILS_OPEN, legacy constant, backward-compat extraction |
| `tests/unit/plan_store/test_draft_pr_lifecycle.py` | Add legacy format extraction test |

## Verification

1. Run lifecycle tests: `uv run pytest tests/unit/plan_store/test_draft_pr_lifecycle.py`
2. Run draft PR backend tests: `uv run pytest tests/unit/plan_store/test_draft_pr_plan_backend.py`
3. Run PR rewrite tests: `uv run pytest tests/commands/pr/test_rewrite.py`
4. Run finalize PR tests: `uv run pytest tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py`
5. Type check: `uv run ty check packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py`