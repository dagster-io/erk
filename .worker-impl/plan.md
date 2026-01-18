# Plan: Reorganize code to eliminate circular import in activation.py

## Problem

PR #5060 has a review comment requesting holistic code reorganization to eliminate a circular import. Currently `activation.py:224` has an inline import:

```python
def print_activation_instructions(script_path: Path) -> None:
    # Import here to avoid circular import
    from erk_shared.output.output import user_output
```

## Root Cause Analysis

The circular import chain:
1. Command files (`up.py`, `down.py`, `wt/checkout_cmd.py`, `branch/checkout_cmd.py`) import from `activation.py` at module level
2. Those same command files also import `user_output` from `erk_shared.output.output`
3. `navigation_helpers.py` already imports both `activation.py` functions AND `user_output`
4. If `activation.py` imported `user_output` at module level, it would create a dependency cycle during CLI startup

## Solution: Move `print_activation_instructions` to `navigation_helpers.py`

The cleanest reorganization is to move the UI-related function `print_activation_instructions` from `activation.py` to `navigation_helpers.py`:

**Why this works:**
- `navigation_helpers.py` already imports `user_output` at module level
- `navigation_helpers.py` already imports from `activation.py` at module level
- This separates concerns: `activation.py` = pure shell script generation, `navigation_helpers.py` = command helpers including UI
- No inline import needed

## Files to Modify

1. **`src/erk/cli/activation.py`**
   - Remove `print_activation_instructions` function (lines 211-230)
   - File becomes pure shell script generation with no output dependencies

2. **`src/erk/cli/commands/navigation_helpers.py`**
   - Add `print_activation_instructions` function (moved from activation.py)
   - Remove it from the `from erk.cli.activation import` statement
   - Function uses the already-imported `user_output`

3. **`src/erk/cli/commands/up.py`**
   - Change import: get `print_activation_instructions` from `navigation_helpers` instead of `activation`

4. **`src/erk/cli/commands/down.py`**
   - Change import: get `print_activation_instructions` from `navigation_helpers` instead of `activation`

5. **`src/erk/cli/commands/branch/checkout_cmd.py`**
   - Change import: get `print_activation_instructions` from `navigation_helpers` instead of `activation`

6. **`src/erk/cli/commands/wt/checkout_cmd.py`**
   - Change import: get `print_activation_instructions` from `navigation_helpers` instead of `activation`

7. **`tests/unit/cli/test_activation.py`**
   - Update imports to get `print_activation_instructions` from `navigation_helpers`

## Verification

1. Run `make fast-ci` to verify no regressions
2. Verify no inline imports remain in activation.py
3. Verify `grep -r "from erk.cli.activation import.*print_activation_instructions"` returns no results

## Related Documentation

- Skills to load: `dignified-python`, `fake-driven-testing`