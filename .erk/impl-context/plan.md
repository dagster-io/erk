# Improve duplicate-check progress output

## Context

The `erk plan duplicate-check` command outputs a single "Checking against N open plan(s)..." line before the LLM call, giving no visibility into which plans are being compared. Error messages are also crammed onto one line. This PR improves the UX with better progress output.

## Changes

### 1. `src/erk/cli/commands/plan/duplicate_check_cmd.py`

**List plans before analysis** (lines 84-86): Replace the single "Checking against N open plan(s)..." message with:
```
Checking against N open plan(s):
  #100: Refactor auth
  #201: Add dark mode
```
Then print `"Analyzing for semantic duplicates..."` before the LLM call (before line 88).

**Multi-line error formatting** (lines 91-94): Split the error into two lines:
```
Error: Duplicate check failed:
  <detail>
```

### 2. `tests/commands/plan/test_duplicate_check.py`

In `test_no_duplicates_found`, add three assertions:
- `"#100: Refactor auth"` appears in output (plan listing)
- `"Analyzing for semantic duplicates"` appears in output
- `"Checking against 1 open plan(s):"` appears in output (colon at end)

## Verification

```
pytest tests/commands/plan/test_duplicate_check.py
```
