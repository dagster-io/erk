# Plan: Remove all "jump" terminology from codebase

## Summary

Full cleanup of all references to the deprecated "jump" command. Replace with appropriate terminology based on context:
- Error messages suggesting worktree navigation → `erk wt goto`
- Internal function names in checkout.py → `_perform_checkout` (matches file name)
- Output messages → "Switched to" (git-like convention)
- Comments/docs → context-appropriate replacement

## Terminology Mapping

| Old | New | Context |
|-----|-----|---------|
| `erk jump {name}` | `erk wt goto {name}` | User-facing error messages |
| `_perform_jump()` | `_perform_checkout()` | Function in checkout.py |
| `"Jumped to worktree X"` | `"Switched to worktree X"` | Output messages |
| `command_name="jump"` | `command_name="checkout"` | Script writer |
| `"jump to {branch}"` | `"checkout {branch}"` | Comments |
| `"jumps to root"` | `"navigates to root"` | Comments |

## Files to Modify

### Source Code (4 files)

1. **src/erk/cli/commands/wt/create_cmd.py** (CRITICAL - the bug)
   - Change `"erk jump {name}"` → `"erk wt goto {name}"`

2. **src/erk/cli/commands/checkout.py** (13 occurrences)
   - Rename `_perform_jump()` → `_perform_checkout()`
   - Update docstrings: "jump" → "checkout" or "switch"
   - Output messages: "Jumped to" → "Switched to"
   - `command_name="jump"` → `command_name="checkout"`
   - `comment=f"jump to {branch}"` → `comment=f"checkout {branch}"`

3. **src/erk/cli/commands/wt/goto_cmd.py** (1 occurrence)
   - Comment: "jumps to root" → "navigates to root"

4. **src/erk/core/script_writer.py** (3 occurrences)
   - Documentation: update command list
   - `command_name="jump"` → `command_name="checkout"`

### Test Files (6 files)

5. **tests/test_utils/context_builders.py**
   - Docstring: "jump" → "goto"

6. **tests/test_utils/env_helpers.py**
   - Function: `test_jump_pure()` → `test_checkout_pure()`
   - Command: `["jump", ...]` → update to match current CLI

7. **tests/commands/navigation/test_checkout.py**
   - Module docstring and all test docstrings
   - Comments referencing "jump"

8. **tests/commands/navigation/test_checkout_messages.py**
   - Module docstring
   - Function names: `test_message_case_2_jumped_*` → `test_message_case_2_switched_*`
   - All `_perform_jump` calls → `_perform_checkout`
   - Docstrings and comments

9. **tests/integration/shell/test_shell_integration.py**
   - Function: `test_shell_integration_jump_*` → `test_shell_integration_checkout_*`
   - Command invocation update

### Documentation (2 files)

10. **docs/agent/cli-output-styling.md**
    - Reference: `jump.py` → `checkout.py`

11. **tests/AGENTS.md**
    - Navigation list: "jump" → "checkout"