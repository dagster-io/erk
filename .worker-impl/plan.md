# Plan: Add `erk objective close` Command

## Overview

Add a CLI command to close objective GitHub issues. The command validates the issue has the `erk-objective` label and closes it.

## Implementation

### 1. Create `src/erk/cli/commands/objective/close_cmd.py`

New command file following the pattern of `list_cmd.py`:

```python
@alias("c")
@click.command("close")
@click.argument("issue_ref")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation")
@click.pass_obj
def close_objective(ctx: ErkContext, issue_ref: str, force: bool) -> None:
```

**Behavior:**
1. Parse `issue_ref` to extract issue number (handle `#123`, `123`, or full URL)
2. Fetch the issue via `ctx.issues.get_issue()`
3. Validate issue has `erk-objective` label (error if not)
4. Validate issue is open (error if already closed)
5. If not `--force`, prompt for confirmation
6. Close via `ctx.issues.close_issue()`
7. Print success message with issue URL

### 2. Update `src/erk/cli/commands/objective/__init__.py`

Register the new command:
```python
from erk.cli.commands.objective.close_cmd import close_objective
register_with_aliases(objective_group, close_objective)
```

### 3. Create Unit Tests

New test file `tests/commands/objective/test_close_objective.py`:
- Test closing an objective issue successfully
- Test error when issue lacks `erk-objective` label
- Test error when issue already closed
- Test `--force` skips confirmation

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/objective/close_cmd.py` | **New** - Command implementation |
| `src/erk/cli/commands/objective/__init__.py` | Register command |
| `tests/commands/objective/test_close_objective.py` | **New** - Unit tests |

## Verification

1. Run `make fast-ci` to verify lint/format/type checks pass
2. Run `pytest tests/commands/objective/test_close_objective.py -v` for new tests
3. Manual test: `erk objective close <issue-number>`