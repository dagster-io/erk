# Plan: Add `--here` flag to `erk implement`

## Summary

Add a `--here` flag to `erk implement` that skips worktree/branch switching and runs the implementation in the current directory.

## Behavior

When `--here` is specified:
1. Skip all worktree pool management (slot allocation, assignment, etc.)
2. Skip branch creation/checkout
3. Create `.impl/` folder in current directory with plan content
4. Execute implementation in current directory

## Flag Constraints

- `--here` is mutually exclusive with `--force` (pool management irrelevant)
- `--here` should work with all execution modes: `--script`, `--no-interactive`, interactive
- `--here` should work with both issue mode and file mode

## Implementation

### 1. Add `--here` flag to command (implement.py)

Add option after `--force`:
```python
@click.option(
    "--here",
    is_flag=True,
    default=False,
    help="Run in current directory without switching worktrees or branches.",
)
```

Add `here: bool` parameter to `implement()` function signature.

### 2. Add validation in validate_flags (implement_shared.py)

Update `validate_flags()` to accept `here` and `force` parameters:
```python
def validate_flags(submit: bool, no_interactive: bool, script: bool, *, here: bool, force: bool) -> None:
```

Add validation:
```python
if here and force:
    raise click.ClickException(
        "--here and --force are mutually exclusive\n"
        "--here runs in current directory (no pool management)\n"
        "--force manages pool slots when switching worktrees"
    )
```

### 3. Create `_implement_here_from_issue` function (implement.py)

New function that:
- Fetches plan from GitHub (reuse `prepare_plan_source_from_issue`)
- Creates `.impl/` folder in `ctx.cwd`
- Saves issue reference
- Executes based on mode (script/non-interactive/interactive)

Key difference: Uses `ctx.cwd` as worktree_path instead of allocated slot.

### 4. Create `_implement_here_from_file` function (implement.py)

New function that:
- Reads plan from file (reuse `prepare_plan_source_from_file`)
- Creates `.impl/` folder in `ctx.cwd`
- Does NOT delete original plan file (no move semantics for --here)
- Executes based on mode

### 5. Update main `implement()` command to dispatch

Add branch before target type detection:
```python
if here:
    if target_info.target_type in ("issue_number", "issue_url"):
        _implement_here_from_issue(...)
    else:
        _implement_here_from_file(...)
else:
    # existing logic
```

### 6. Add dry-run support for --here

Create `_show_dry_run_output_here()` that shows:
- "Would run in current directory: {ctx.cwd}"
- Plan source info
- Command sequence

## Files to Modify

1. `src/erk/cli/commands/implement.py` - Add flag, new functions, dispatch logic
2. `src/erk/cli/commands/implement_shared.py` - Update `validate_flags()` signature

## Verification

1. Run `erk implement 123 --here --dry-run` - should show current directory
2. Run `erk implement ./plan.md --here --dry-run` - should show current directory
3. Run `erk implement 123 --here --force` - should error (mutually exclusive)
4. Test interactive, non-interactive, and script modes with `--here`
5. Verify `.impl/` folder created in current directory