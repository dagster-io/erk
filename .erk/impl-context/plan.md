# Break test_exit_plan_mode_hook.py into a subpackage

## Context

`tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py` is ~1072 lines with 6 test classes, each testing a distinct function. The file should be split into a subpackage with one file per tested function, following the project's documented pattern for large test files.

## Plan

Replace the single file with a directory:

```
tests/unit/cli/commands/exec/scripts/exit_plan_mode_hook/
├── __init__.py
├── test_determine_exit_action.py      (~170 lines - TestDetermineExitAction)
├── test_extract_plan_title.py         (~60 lines - TestExtractPlanTitle)
├── test_is_terminal_editor.py         (~50 lines - TestIsTerminalEditor)
├── test_abbreviate_for_header.py      (~35 lines - TestAbbreviateForHeader)
├── test_build_blocking_message.py     (~480 lines - TestBuildBlockingMessage)
├── test_hook_integration.py           (~220 lines - TestHookIntegration)
```

Each file gets:
- Only the imports it needs (not the full import block from the original)
- The test class moved verbatim (no structural changes to tests themselves)

Delete the original `test_exit_plan_mode_hook.py` after creating all subpackage files.

## Files to modify

- **Delete**: `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`
- **Create**: 7 new files in `tests/unit/cli/commands/exec/scripts/exit_plan_mode_hook/`

## Verification

- Run `pytest tests/unit/cli/commands/exec/scripts/exit_plan_mode_hook/` to confirm all tests pass
- Verify test count matches the original file
