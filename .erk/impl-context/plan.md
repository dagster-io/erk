# Plan: Migrate stack/move_cmd.py to Ensure-Based Error Handling

Part of Objective #7160, Node 3.1

## Context

`src/erk/cli/commands/stack/move_cmd.py` contains 8 instances of the legacy `user_output("Error: ...") + raise SystemExit(1)` pattern. This objective migrates these to the `Ensure` class / `UserFacingCliError` pattern for consistent, styled error handling across the CLI.

## Pattern Analysis

All 8 patterns in `move_cmd.py` follow `user_output(f"Error: ...") + raise SystemExit(1)`. Each maps to an `Ensure` method or `UserFacingCliError`:

| # | Location | Current Pattern | Migration Target |
|---|----------|----------------|-----------------|
| 1 | `_resolve_current_worktree` L33-38 | Not in any worktree | `raise UserFacingCliError(...)` |
| 2 | `resolve_source_worktree` L60-61 | Multiple source flags | `Ensure.invariant(flag_count <= 1, ...)` |
| 3 | `resolve_source_worktree` L83-84 | Invalid state - no source | `raise RuntimeError(...)` (programmer error, unreachable) |
| 4 | `execute_move` L119-124 | Uncommitted changes in source | `raise UserFacingCliError(...)` |
| 5 | `execute_move` L138-143 | Uncommitted changes in target | `raise UserFacingCliError(...)` |
| 6 | `execute_swap` L181-183 | Both worktrees need branches | `Ensure.invariant(...)` |
| 7 | `execute_swap` L189-194 | Uncommitted changes detected | `raise UserFacingCliError(...)` |
| 8 | `move_stack` L297-298 | Source and target are same | `Ensure.invariant(...)` |

## Implementation

### File: `src/erk/cli/commands/stack/move_cmd.py`

**Import change:** Add `UserFacingCliError` to the existing `Ensure` import line:
```python
from erk.cli.ensure import Ensure, UserFacingCliError
```

**Pattern 1** — `_resolve_current_worktree` (L33-38): Replace `user_output` + `SystemExit(1)` with `raise UserFacingCliError(...)`. Keep multiline message with remediation hints.

**Pattern 2** — `resolve_source_worktree` (L60-61): Replace with `Ensure.invariant(flag_count <= 1, "Only one of --current, --branch, or --worktree can be specified")`.

**Pattern 3** — `resolve_source_worktree` (L83-84): Replace with `raise RuntimeError("Invalid state - no source specified")`. This is an impossible code path (programmer error), not a user-facing condition.

**Patterns 4, 5, 7** — Uncommitted changes guards: Replace each `user_output` + `SystemExit(1)` block with a single-line condition + `raise UserFacingCliError(...)`. Preserve the multiline error messages with remediation hints.

**Pattern 6** — `execute_swap` (L181-183): Replace with `Ensure.invariant(source_branch is not None and target_branch is not None, "Both worktrees must have branches checked out for swap")`.

**Pattern 8** — `move_stack` (L297-298): Replace with `Ensure.invariant(source_wt.resolve() != target_wt.resolve(), "Source and target worktrees are the same")`.

### No test changes required

Existing tests in `tests/commands/workspace/test_move.py` assert on `result.exit_code == 1` and error message substrings. `UserFacingCliError` preserves both: exit code 1 (via Click's exception handling) and the same error message text (minus the "Error: " prefix which Click adds via `.show()`).

**One subtlety**: Tests currently check for strings like `"Only one of --current"` in `result.output`. With `Ensure.invariant` / `UserFacingCliError`, Click outputs `"Error: "` prefix automatically. The test assertions use substring matching (`in result.output`), so they will continue to pass since the core message text is preserved.

## Verification

1. Run scoped tests: `uv run pytest tests/commands/workspace/test_move.py`
2. Run type checker on the file: `uv run ty check src/erk/cli/commands/stack/move_cmd.py`
3. Verify zero `raise SystemExit(1)` remains in move_cmd.py (grep)
4. Run lint: `uv run ruff check src/erk/cli/commands/stack/move_cmd.py`
