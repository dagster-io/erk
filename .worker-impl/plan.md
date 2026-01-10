# Fix Test Assertion for PR Number Format

## Problem

The test `test_includes_statusline_context_with_all_fields` in `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py` is failing because:

- **Test expects**: `(gh:#4230)` - the old format
- **Code produces**: `(pr:#4230)` - the new format

This mismatch was introduced in commit `bd7568c94` ("Add branch context header to plan mode exit prompt") which intentionally changed the PR identifier from `gh:` to `pr:` prefix for consistency, but the test assertion on line 615 was not updated.

## Root Cause

In `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` line 286:
```python
statusline_parts.append(f"pr:#{pr_number}")  # Changed from gh:# to pr:#
```

But the test still asserts the old format:
```python
assert "(gh:#4230)" in message  # Line 615 - expects old format
```

## Solution

Update the test assertion to match the new format. Change line 615 from:
```python
assert "(gh:#4230)" in message
```
to:
```python
assert "(pr:#4230)" in message
```

Also update the related test `test_includes_statusline_context_partial` at line 639 which checks for the absence of PR context:
```python
assert "(gh:#" not in message  # Should be "(pr:#" for consistency
```
to:
```python
assert "(pr:#" not in message
```

## Files to Modify

1. `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`
   - Line 615: Change `gh:#4230` to `pr:#4230`
   - Line 639: Change `gh:#` to `pr:#`

## Verification

Run the targeted test file:
```bash
make test-unit-erk  # or scoped: pytest tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py
```