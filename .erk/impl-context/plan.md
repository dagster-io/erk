# Fix: Rocket emoji should not appear on draft PRs

## Context

The erk dash TUI shows a rocket emoji (🚀) in the "sts" column for PRs that are "ready to land" — checks passing, no conflicts, no unresolved comments. However, draft PRs can also show the rocket, which is misleading since draft PRs can't actually be landed/merged.

This happens because the rocket condition in `_build_indicators()` checks `is_impl`, `has_conflicts`, `review_decision`, `checks_passing`, and `has_unresolved_comments` — but never checks `is_draft`.

## Change

**File: `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`** (line 227)

Add `is_draft is not True` to the rocket emoji condition:

```python
# Before:
if is_impl and has_conflicts is not True and review_decision != "CHANGES_REQUESTED":

# After:
if is_impl and is_draft is not True and has_conflicts is not True and review_decision != "CHANGES_REQUESTED":
```

**File: `tests/unit/plan_store/test_lifecycle_display.py`** (lines 476-486)

Update `test_impl_draft_checks_passing_shows_rocket` — it currently asserts the **broken** behavior (expects `🚧 🚀`). Change it to assert draft impl PRs do NOT get the rocket:

```python
def test_impl_draft_checks_passing_no_rocket() -> None:
    """Draft impl with passing checks does not show rocket — draft PRs aren't landable."""
    # ... is_draft=True, checks_passing=True ...
    assert result == "[yellow]impl 🚧[/yellow]"
```

## Verification

Run the lifecycle display tests:
```
uv run pytest tests/unit/plan_store/test_lifecycle_display.py
```
