# Fix TUI plan body displaying footer instead of content for rewritten draft PRs

## Context

When viewing a draft PR plan in the TUI body screen (press `v`), rewritten PRs (e.g., PR #7626 after remote implementation) show only the footer ("Closes #7626" + checkout command) instead of the actual content (Summary, Files Changed, Key Changes sections).

**Root cause**: `DraftPRPlanListService.get_plan_list_data()` calls `extract_plan_content(pr_details.body)` which:
1. Looks for `<details><summary><code>original-plan</code></summary>` — NOT FOUND (rewritten bodies don't have this)
2. Falls back to content after `\n\n---\n\n` separator — returns the **footer** (Closes + checkout) instead of the AI summary

For Stage 1/2 bodies with the `original-plan` details section, the function works correctly. The bug only affects rewritten bodies where the `\n\n---\n\n` separator is between content and footer, not between metadata and content.

## Fix

**File**: `src/erk/core/services/plan_list_service.py` (master version with `DraftPRPlanListService`)

In the `get_plan_list_data()` loop, after calling `extract_plan_content()`, detect when the body has no `original-plan` details section. In that case, use `extract_main_content()` from `pr_footer.py` which correctly strips the footer and returns the main body content.

```python
# Current code (line ~85):
plan_body = extract_plan_content(pr_details.body)

# New code:
plan_body = extract_plan_content(pr_details.body)
# extract_plan_content falls back to content-after-separator for bodies
# without <details>original-plan</details>. For rewritten PRs this
# returns the footer instead of the AI summary. Use extract_main_content
# which strips the footer via rsplit on \n---\n.
if (DETAILS_OPEN not in pr_details.body
        and _LEGACY_DETAILS_OPEN not in pr_details.body):
    plan_body = extract_main_content(pr_details.body)
```

**New imports needed**:
```python
from erk_shared.gateway.github.pr_footer import extract_main_content
from erk_shared.plan_store.draft_pr_lifecycle import (
    DETAILS_OPEN,
    _LEGACY_DETAILS_OPEN,
    extract_plan_content,
)
```

Note: `_LEGACY_DETAILS_OPEN` is a module-private constant. It should be exported (rename to `LEGACY_DETAILS_OPEN`) or a helper function should be added to `draft_pr_lifecycle.py` like `has_original_plan_section(body: str) -> bool`.

**Preferred approach**: Add a helper function to `draft_pr_lifecycle.py`:

```python
def has_original_plan_section(pr_body: str) -> bool:
    """Check if a PR body contains the original-plan details section."""
    return DETAILS_OPEN in pr_body or _LEGACY_DETAILS_OPEN in pr_body
```

Then in the list service:
```python
from erk_shared.plan_store.draft_pr_lifecycle import (
    extract_plan_content,
    has_original_plan_section,
)
from erk_shared.gateway.github.pr_footer import extract_main_content

# In the loop:
plan_body = extract_plan_content(pr_details.body)
if not has_original_plan_section(pr_details.body):
    plan_body = extract_main_content(pr_details.body)
```

## Files to modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py` | Add `has_original_plan_section()` helper |
| `src/erk/core/services/plan_list_service.py` | Use `extract_main_content()` fallback when no original-plan section |
| `tests/unit/services/test_plan_list_service.py` | Add test for rewritten PR body display content |

## Key existing functions to reuse

- `extract_main_content()` in `packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py:119` — strips header and footer from PR body using `rsplit("\n---\n", 1)`
- `extract_plan_content()` in `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py:123` — existing extraction, unchanged
- `DETAILS_OPEN` / `_LEGACY_DETAILS_OPEN` constants in `draft_pr_lifecycle.py:87-88`

## Verification

1. Run `make fast-ci` to confirm no regressions
2. Run the new test specifically: `pytest tests/unit/services/test_plan_list_service.py -k rewritten`
3. Manual: `erk dash -i`, press `v` on a draft PR that has been through remote implementation (like #7626) — should display the full Summary/Files Changed/Key Changes content instead of just the footer
