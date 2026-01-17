# Plan: Add --dangerous variant to erk prepare output

## Summary

Add a third option to the activation instructions printed by `erk prepare` that includes the `--dangerous` flag for `erk implement --here`.

## Change

**File:** `src/erk/cli/activation.py` (lines 235-237)

**Current output:**
```
To activate the worktree environment:
  source /path/to/.erk/activate.sh

To activate and start implementation:
  source /path/to/.erk/activate.sh && erk implement --here
```

**New output:**
```
To activate the worktree environment:
  source /path/to/.erk/activate.sh

To activate and start implementation:
  source /path/to/.erk/activate.sh && erk implement --here

To activate and start implementation (skip permission prompts):
  source /path/to/.erk/activate.sh && erk implement --here --dangerous
```

## Implementation

Add two additional `user_output` calls after line 237 in `print_activation_instructions()`:

```python
if include_implement_hint:
    user_output("\nTo activate and start implementation:")
    user_output(f"  source {script_path} && erk implement --here")
    user_output("\nTo activate and start implementation (skip permission prompts):")
    user_output(f"  source {script_path} && erk implement --here --dangerous")
```

## Verification

Run `erk prepare <issue_number>` and verify the new output includes the `--dangerous` variant.