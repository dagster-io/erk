# Plan: Add Prepare+Implement One-Liner to CLI Output

## Summary

Add the TUI's "prepare+activate+implement" one-liner command to the CLI's "next steps" output, giving users a single copy-paste option that combines `erk prepare` with shell activation and implementation.

## Current State

**TUI shows (via key `[4]`):**
```bash
source "$(erk prepare 5509 --script)" && erk implement --dangerous
```

**CLI `format_next_steps_plain()` shows:**
```
OR exit Claude Code first, then run one of:
  Local: erk prepare 5509
  Local (dangerously): erk prepare -d 5509
  Submit to Queue: erk plan submit 5509
```

The CLI is missing the combined one-liner option.

## Implementation

### Files to Modify

1. **`packages/erk-shared/src/erk_shared/output/next_steps.py`**
   - Add `prepare_and_implement` property to `IssueNextSteps` dataclass
   - Update `format_next_steps_plain()` to include the one-liner option

2. **`.claude/commands/erk/plan-save.md`**
   - Update the "Display Results" template to include the one-liner

3. **`tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py`**
   - Update assertions to verify the new output line

### Changes

**next_steps.py - Add property:**
```python
@property
def prepare_and_implement(self) -> str:
    return f'source "$(erk prepare {self.issue_number} --script)" && erk implement --dangerous'
```

**next_steps.py - Update format_next_steps_plain():**
```
OR exit Claude Code first, then run one of:
  Local: erk prepare {issue_number}
  Local (dangerously): erk prepare -d {issue_number}
  Prepare+Implement: source "$(erk prepare {issue_number} --script)" && erk implement --dangerous
  Submit to Queue: erk plan submit {issue_number}
```

**plan-save.md - Update template similarly**

## Verification

1. Run unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py -v`
2. Manual test: Run `erk exec plan-save-to-issue` and verify the one-liner appears in output