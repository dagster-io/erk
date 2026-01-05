# Plan: Add check counts to status line

## Goal
Display detailed check counts in the status line instead of just a single emoji.

## Current vs New Format

**Current:** `chks:🔄`

**New:** `chks:3✅ 1🚫 2🔄` (only show non-zero counts)

Examples:
- All pass: `chks:5✅`
- Some pending: `chks:3✅ 2🔄`
- Failures: `chks:3✅ 1🚫 1🔄`
- No checks: (omit entirely, same as current)

## Files to Modify

### `packages/erk-statusline/src/erk_statusline/statusline.py`

1. **Modify `_categorize_check_buckets()`** (lines 511-567):
   - Change return type from `str` to `tuple[int, int, int]` (pass, fail, pending counts)
   - Count checks in each bucket instead of just setting flags

2. **Modify `get_checks_status()`** (lines 570-585):
   - Change return type to format counts as string
   - Build string like `3✅ 1🚫 2🔄` from counts
   - Only include non-zero counts
   - Return empty string if all counts are zero

3. **`build_gh_label()`** - no change needed (already uses `get_checks_status()`)

### `packages/erk-statusline/tests/test_statusline.py`

Update tests for:
- `_categorize_check_buckets()` - now returns tuple of counts
- `get_checks_status()` - now returns formatted count string

## Implementation Steps

1. Update `_categorize_check_buckets()` to return `(pass_count, fail_count, pending_count)`
2. Update `get_checks_status()` to format counts into display string
3. Update existing tests
4. Run tests to verify