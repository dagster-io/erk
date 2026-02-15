# Plan: Make one-shot a Hidden Command

## Context

The `erk one-shot` command is currently visible in the CLI help output. The task is to make it a hidden command so it doesn't appear in the standard help text but can still be invoked directly by users who know about it.

This is a simple change following an existing pattern in the codebase. The `erk wt current` command at `src/erk/cli/commands/wt/current_cmd.py:13` already demonstrates the pattern: `@click.command("current", hidden=True)`.

## Changes Required

### File to Modify

**`src/erk/cli/commands/one_shot.py`** (line 47)

Currently:
```python
@click.command("one-shot")
```

Change to:
```python
@click.command("one-shot", hidden=True)
```

This single-line change adds the `hidden=True` parameter to the Click decorator, which will hide the command from the standard help output while keeping it fully functional.

## Files NOT Changing

- **Tests**: No test changes needed. The existing tests in `tests/commands/one_shot/test_one_shot.py` and `tests/commands/one_shot/test_branch_name.py` will continue to work unchanged. The `hidden` parameter only affects help text display, not functionality.

- **CLI registration**: `src/erk/cli/cli.py` doesn't need changes. The command registration at line 207 (`cli.add_command(one_shot)`) remains the same.

- **Slash command**: `.claude/commands/erk/one-shot.md` doesn't need changes. It calls `erk one-shot` which will still work.

- **Documentation**: No learned docs found referencing this command, so no documentation updates needed.

## Implementation Details

The `hidden` parameter is a standard Click feature that:
- Hides the command from `erk --help` output
- Keeps the command fully functional when invoked directly
- Doesn't affect command behavior or error messages
- Is widely used in Click CLIs for internal/experimental commands

## Verification

After making the change:

1. Verify the command still works:
   ```bash
   erk one-shot "test instruction" --dry-run
   ```
   This should execute normally and show the dry-run output.

2. Verify the command is hidden from help:
   ```bash
   erk --help
   ```
   The output should NOT include `one-shot` in the command list.

3. Run the existing tests:
   ```bash
   pytest tests/commands/one_shot/ -v
   ```
   All tests should pass unchanged since the functionality remains identical.