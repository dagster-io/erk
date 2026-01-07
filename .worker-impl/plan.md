# Plan: Rename `erk submit` to `erk plan submit`

## Summary

Replace all references to `erk submit` with `erk plan submit` throughout the codebase. The command was moved but some references weren't updated.

## Files to Modify

### Production Code

1. **`packages/erk-shared/src/erk_shared/output/next_steps.py:30`**
   - Change: `return f"erk submit {self.issue_number}"` → `return f"erk plan submit {self.issue_number}"`

2. **`src/erk/cli/commands/submit.py:681-683`** (docstring examples)
   - Change: `erk submit 123` → `erk plan submit 123`
   - Change: `erk submit 123 456 789` → `erk plan submit 123 456 789`
   - Change: `erk submit 123 --base master` → `erk plan submit 123 --base master`

3. **`src/erk/cli/commands/plan/create_cmd.py:120`**
   - Change: `Submit:     erk submit` → `Submit:     erk plan submit`

4. **`packages/erk-shared/src/erk_shared/github/metadata/schemas.py:131`** (docstring)
   - Change: `(posted by erk submit)` → `(posted by erk plan submit)`

5. **`packages/erk-shared/src/erk_shared/github/status_history.py:96`**
   - Change: `"reason": "erk submit executed"` → `"reason": "erk plan submit executed"`

### Test Code

6. **`tests/commands/plan/test_create.py:34`**
   - Change: `assert "Submit:     erk submit 1"` → `assert "Submit:     erk plan submit 1"`

7. **`tests/shared/github/test_status_history.py:200`**
   - Change: `assert history[0]["reason"] == "erk submit executed"` → `assert ... == "erk plan submit executed"`

8. **`tests/unit/fakes/test_fake_command_executor.py:18-19`**
   - Change: `"erk submit 456"` → `"erk plan submit 456"`

9. **`tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py:164`**
   - Change: `assert "Submit to Queue: erk submit 1"` → `assert "Submit to Queue: erk plan submit 1"`

10. **`tests/unit/gateways/github/metadata_blocks/test_format_plan_body.py:34`**
    - Change: `assert "erk submit" not in result` → `assert "erk plan submit" not in result`

## Notes

- `tests/commands/submit/test_basic_submission.py:73` - This is a test name/description, not a command reference (plan title). No change needed.