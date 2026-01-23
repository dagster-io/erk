# Add `-f`/`--force` Flag to `erk plan submit` for TUI Support

## Problem

The TUI runs `erk plan submit` via `run_streaming_command()` which sets `stdin=subprocess.DEVNULL`. When existing branches are found (pattern `P{issue}-*`), the command prompts for user input, causing "Aborted!" because there's no interactive terminal.

Screenshot shows: Plan #5722 fails at "Use existing branch 'P5722-status-line-pr-display-in-01-23-1455'? [Y/n]: Aborted!"

## Solution

Add a `-f`/`--force` flag to `erk plan submit` that skips the branch reuse prompts and automatically deletes existing branches to create a fresh one.

**Policy when `-f` is passed:**
- If existing branches found: Delete them all and create a new branch
- If no existing branches: Create new branch normally
- Rationale: When resubmitting from TUI, you want a clean slate rather than continuing from a potentially broken previous attempt

## Files to Modify

### 1. `src/erk/cli/commands/submit.py`

**Add force flag to command definition (around line 793-802):**
```python
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Delete existing branches and create fresh without prompting.",
)
```

**Modify `_prompt_existing_branch_action()` (lines 107-140):**
- Add `force: bool` parameter (keyword-only)
- When `force=True`: delete existing branches, return None (signals create new)

**Modify `_validate_issue_for_submit()` (around line 295):**
- Add `force: bool` parameter (keyword-only)
- Pass to `_prompt_existing_branch_action()`

**Update `submit_cmd()` (line 802):**
- Accept `force` parameter from Click
- Pass through to `_validate_issue_for_submit()`

### 2. `src/erk/tui/screens/plan_detail_screen.py` (line 676)

Change:
```python
["erk", "plan", "submit", str(row.issue_number)]
```
To:
```python
["erk", "plan", "submit", str(row.issue_number), "-f"]
```

### 3. `src/erk/tui/app.py` (if similar invocation exists)

Add `-f` flag to any `erk plan submit` invocations.

### 4. `src/erk/tui/data/provider.py` (line 366-382)

Update `submit_to_queue()` method to pass `-f`:
```python
["erk", "plan", "submit", str(issue_number), "-f"]
```

### 5. `tests/commands/submit/test_existing_branch_detection.py`

Add tests for force mode:
- `test_submit_force_deletes_existing_branches_and_creates_new()` - verify no `confirm()` calls, deletes existing, creates fresh branch
- `test_submit_force_creates_new_branch_when_none_exist()` - verify normal flow when no existing branches (no-op for force)

## Implementation Approach

The `_prompt_existing_branch_action()` function change:

```python
def _prompt_existing_branch_action(
    ctx: ErkContext,
    repo_root: Path,
    existing_branches: list[str],
    new_branch_name: str,
    *,
    force: bool,  # NEW - required keyword-only
) -> str | None:
    if force:
        # Delete all existing branches and signal to create new
        user_output(f"\nDeleting {len(existing_branches)} existing branch(es) (--force mode):")
        for branch in existing_branches:
            ctx.branch_manager.delete_branch(repo_root, branch, force=True)
            user_output(f"  Deleted: {branch}")
        return None  # None signals "create new branch"

    # ... existing prompt logic unchanged
```

## Verification

1. **Manual TUI test:**
   - Create a plan issue with existing P{issue}-* branch
   - Open TUI with `erk dash -i`
   - Select plan, run "Submit to Queue" action
   - Verify: Deletes existing branch, creates new one, no "Aborted!"

2. **Unit tests:**
   ```bash
   uv run pytest tests/commands/submit/test_existing_branch_detection.py -v
   ```

3. **CLI test:**
   ```bash
   # Create existing branch scenario, then:
   erk plan submit 123 -f
   # Should delete existing branch(es) and create fresh one without prompting
   ```

## Related Documentation

- `docs/learned/cli/ci-aware-commands.md` - CI detection patterns (optional enhancement)
- `docs/learned/tripwires.md` - Force flag short form `-f` convention
- `fake-driven-testing` skill - Test patterns with FakeConsole