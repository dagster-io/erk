# Plan: Add `--here` Flag to `erk implement`

**Part of Objective #4954, Phase 1**

## Summary

Add a `--here` flag to `erk implement` that implements the plan in the current worktree/branch instead of creating a new pool slot.

## Goal

```bash
erk implement 123 --here        # Implement plan #123 in current worktree
erk implement ./plan.md --here  # Implement from file in current worktree
```

When `--here` is used:
- No pool slot allocation
- No worktree creation/checkout
- `.impl/` folder created in `ctx.cwd`
- Execution happens in current directory

## Implementation

### 1. Add `--here` flag to command

**File:** `src/erk/cli/commands/implement.py`

Add after `--force` option:
```python
@click.option(
    "--here",
    is_flag=True,
    help="Implement in current worktree instead of creating a new pool slot.",
)
```

Update `implement()` signature to include `here: bool`.

### 2. Validate `--here` + `--force` incompatibility

In `implement()` after flag handling:
```python
if here and force:
    raise click.ClickException(
        "--force is for pool slot management, not compatible with --here"
    )
```

### 3. Create `_implement_here_from_issue()` function

New function that:
1. Discovers repo context from `ctx.cwd`
2. Fetches plan via `ctx.plan_store.get_plan()`
3. Validates plan has `erk-plan` label
4. Handles dry-run: show what would happen, return early
5. Creates `.impl/` folder in current worktree using `create_impl_folder(worktree_path=ctx.cwd, ...)`
6. Saves issue reference using `save_issue_reference()`
7. Executes via existing `execute_interactive_mode()` / `execute_non_interactive_mode()` / script output
   - Pass `ctx.cwd` as `worktree_path`

### 4. Create `_implement_here_from_file()` function

Similar to issue version:
1. Read plan file content via `prepare_plan_source_from_file()`
2. Handle dry-run
3. Create `.impl/` folder in current worktree
4. Delete original plan file (move semantics, same as worktree mode)
5. Execute via existing helpers

### 5. Add dispatch logic in `implement()`

After target detection, before existing worktree creation:
```python
if here:
    if target_info.target_type in ("issue_number", "issue_url"):
        _implement_here_from_issue(
            ctx,
            issue_number=target_info.issue_number,
            dry_run=dry_run,
            submit=submit,
            dangerous=dangerous,
            script=script,
            no_interactive=no_interactive,
            verbose=verbose,
            model=model,
            executor=ctx.claude_executor,
        )
    else:
        _implement_here_from_file(
            ctx,
            plan_file=Path(target),
            dry_run=dry_run,
            submit=submit,
            dangerous=dangerous,
            script=script,
            no_interactive=no_interactive,
            verbose=verbose,
            model=model,
            executor=ctx.claude_executor,
        )
    return
```

## Files to Modify

| File | Changes |
|------|---------|
| `src/erk/cli/commands/implement.py` | Add `--here` flag, `_implement_here_from_issue()`, `_implement_here_from_file()`, dispatch logic |
| `tests/commands/implement/test_here_flag.py` | New test file for `--here` behavior |

## Tests

**New file:** `tests/commands/implement/test_here_flag.py`

1. `test_implement_here_from_issue_creates_impl_in_cwd()` - `.impl/` created in current dir, no slot
2. `test_implement_here_from_file_creates_impl_in_cwd()` - same for file mode
3. `test_implement_here_from_file_deletes_original()` - plan file is deleted
4. `test_implement_here_with_dry_run()` - no mutation, shows "Would create .impl/ in current directory"
5. `test_implement_here_with_force_errors()` - incompatible flags error
6. `test_implement_here_with_script_generates_script()` - script mode works with --here

## Verification

1. **Run tests:**
   ```bash
   uv run pytest tests/commands/implement/test_here_flag.py -v
   ```

2. **Manual testing:**
   ```bash
   # Dry run - should show impl in cwd, no slot allocation
   erk implement 123 --here --dry-run

   # With file
   erk implement ./plan.md --here --dry-run

   # Error case
   erk implement 123 --here --force  # Should error
   ```

## Related Documentation

- Skills: `dignified-python`, `fake-driven-testing`
- Reference: `docs/learned/cli/`, `docs/learned/testing/`