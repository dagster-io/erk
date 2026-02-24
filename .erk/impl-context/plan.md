# Fix: Rocket emoji blocked by eyes emoji in dash

## Context

PR #8017 has 18/18 checks passing, 1/1 comments resolved, no conflicts, not a draft — yet no 🚀 appears. The `👀` (published PR) indicator is treated as a "blocking" indicator that prevents the rocket from showing.

In `_build_indicators()` at `lifecycle.py:232`:
```python
has_blocking_indicators = any(i != "🥞" for i in indicators)
```

This excludes 🥞 (stacked) from blocking the rocket, but not 👀 (published). Since every real non-draft PR gets `👀`, the rocket can **never** appear for any published PR. The test that passes (`test_impl_checks_passing_no_comments_shows_rocket`) only works because it sets `is_draft=None`, sidestepping the issue.

## Fix

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`

Change line 232 from:
```python
has_blocking_indicators = any(i != "🥞" for i in indicators)
```
to:
```python
has_blocking_indicators = any(i not in ("🥞", "👀", "🚧") for i in indicators)
```

Both `👀` (published) and `🚧` (draft) are informational status indicators, not blockers. Only `💥` (conflicts) and `❌` (changes requested) should block the rocket.

**File:** `tests/unit/plan_store/test_lifecycle_display.py`

Update `test_impl_checks_passing_no_comments_shows_rocket` to use `is_draft=False` (realistic case) and assert the result includes both `👀` and `🚀`. Add a new test confirming draft PRs also get the rocket when checks pass.

## Verification

- Run: `uv run pytest tests/unit/plan_store/test_lifecycle_display.py`
- Confirm existing tests pass and new/updated tests cover the fix
