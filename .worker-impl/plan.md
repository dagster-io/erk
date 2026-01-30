# Plan: Introduce `UserFacingCliError` and fix `RuntimeError` misuse

## Problem

`raise RuntimeError(push_result.message)` is used in 8 places across CLI commands to handle `PushError` discriminated union results. `RuntimeError` is wrong here:
- Produces ugly tracebacks (no catch in `test_plan_implement_gh_workflow`)
- Doesn't express intent — this is a *user-facing error*, not a programming bug
- The existing two-line pattern (`user_output(...)` + `raise SystemExit(1)`) is correct but verbose

## Solution

### 1. Create `UserFacingCliError` in `src/erk/cli/ensure.py`

A data-carrying exception — no side effects in `__init__`, printing happens at the entry point.

```python
class UserFacingCliError(Exception):
    """Exception for user-facing CLI errors.

    Stores the error message for display at the CLI entry point.
    Caught by main() which handles styled output and exit code.

    Usage:
        raise UserFacingCliError("Not a GitHub repository")
        raise UserFacingCliError(push_result.message)
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
```

### 2. Add catch block in `main()` entry point (`src/erk/cli/cli.py`)

Single place that handles all `UserFacingCliError` display:

```python
def main() -> None:
    """CLI entry point used by the `erk` console script."""
    entry_id = log_command_start(get_cli_args(), Path.cwd())
    register_exit_handler(entry_id)

    try:
        cli()
    except UserFacingCliError as e:
        user_output(click.style("Error: ", fg="red") + e.message)
        raise SystemExit(1) from None
```

Click's standalone mode lets non-Click exceptions propagate, so `UserFacingCliError` reaches `main()`.

### 3. Fix all `raise RuntimeError(push_result.message)` → `raise UserFacingCliError(...)`

8 occurrences across 5 files:

| File | Line | Context |
|------|------|---------|
| `src/erk/cli/commands/admin.py` | 198 | push current branch |
| `src/erk/cli/commands/admin.py` | 226 | push master to test branch |
| `src/erk/cli/commands/admin.py` | 239 | push after empty commit |
| `src/erk/cli/commands/submit.py` | 466 | push branch to remote |
| `src/erk/cli/commands/submit.py` | 595 | push placeholder commit |
| `src/erk/cli/commands/pr/submit_pipeline.py` | 319 | push in pipeline step |
| `src/erk/cli/commands/pr/sync_cmd.py` | 123 | force push after sync |
| `src/erk/cli/commands/exec/scripts/plan_create_review_branch.py` | 183 | push review branch |

Each becomes:
```python
if isinstance(push_result, PushError):
    raise UserFacingCliError(push_result.message)
```

### 4. Refactor `Ensure` class to use `UserFacingCliError` internally

Every `Ensure` method currently does the two-line pattern. Refactor internals to:
```python
@staticmethod
def invariant(condition: bool, error_message: str) -> None:
    if not condition:
        raise UserFacingCliError(error_message)
```

This keeps the `Ensure` public API unchanged but dogfoods the new type. ~18 changes within `ensure.py`.

### 5. Update documentation

**`docs/learned/cli/output-styling.md`** — Add `UserFacingCliError` section:
- When to use: mid-function errors where `Ensure` precondition checks don't fit
- Relationship to `Ensure`: Ensure uses it internally; both are valid at call sites
- Decision guide: Ensure for preconditions, `UserFacingCliError` for mid-logic errors
- Show the one-liner pattern: `raise UserFacingCliError(push_result.message)`

**`docs/learned/architecture/discriminated-union-error-handling.md`** — Update Consumer Pattern:
- Show `UserFacingCliError` as the CLI-layer consumer pattern for discriminated unions
- Replace the `click.echo` + `return 1` example with `raise UserFacingCliError(...)`

## Files to modify

1. `src/erk/cli/ensure.py` — Add `UserFacingCliError` class, refactor Ensure methods
2. `src/erk/cli/cli.py` — Add try/except in `main()`
3. `src/erk/cli/commands/admin.py` — 3 RuntimeError → UserFacingCliError
4. `src/erk/cli/commands/submit.py` — 2 RuntimeError → UserFacingCliError
5. `src/erk/cli/commands/pr/submit_pipeline.py` — 1 RuntimeError → UserFacingCliError
6. `src/erk/cli/commands/pr/sync_cmd.py` — 1 RuntimeError → UserFacingCliError
7. `src/erk/cli/commands/exec/scripts/plan_create_review_branch.py` — 1 RuntimeError → UserFacingCliError
8. `docs/learned/cli/output-styling.md` — Add UserFacingCliError section
9. `docs/learned/architecture/discriminated-union-error-handling.md` — Update consumer pattern

## Verification

1. Run `ruff check` and `ruff format` on changed Python files
2. Run `ty` for type checking
3. Run existing tests for affected commands
4. Grep to confirm zero remaining `raise RuntimeError(push_result.message)` in CLI code