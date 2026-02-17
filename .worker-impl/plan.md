# Add count argument to `erk up` and `erk down`

## Context

The `erk up` and `erk down` commands currently navigate exactly one level in the branch stack. Graphite's `gt up` and `gt down` commands accept an optional numeric argument to move N levels at once (e.g., `gt up 3` moves up 3 branches). This plan adds the same capability to erk's navigation commands.

## Design Decisions

### Approach: Loop over single-step resolution

Rather than using `get_branch_stack()` to compute the full stack and index into it, the implementation loops the existing single-step `resolve_up_navigation` / `resolve_down_navigation` functions N times. This is simpler, preserves existing validation (e.g., multiple-children check for up), and matches the mental model of "move up N times."

### `--delete-current` interaction with count

`--delete-current` is **incompatible** with count > 1. When `--delete-current` is used, count must be 1 (the default). The command should error if the user passes both `--delete-current` and a count > 1. Deleting intermediate branches during multi-step navigation is undefined behavior and dangerous.

### Click argument style

Use `@click.argument("count", type=int, default=1, required=False)` to match the `gt up N` / `gt down N` positional style. The argument is optional with a default of 1, so `erk up` still works as before and `erk up 3` moves 3 levels.

### Validation

- `count` must be >= 1 (validated with `Ensure.invariant`)
- `count > 1` is incompatible with `--delete-current` (validated with `Ensure.invariant`)

## Changes

### 1. `src/erk/cli/commands/up.py`

Add a `count` Click argument and pass it through to `execute_stack_navigation`.

```python
@click.command("up", cls=GraphiteCommandWithHiddenOptions)
@click.argument("count", type=int, default=1, required=False)
@script_option
@click.option(
    "--delete-current",
    is_flag=True,
    help="Delete current branch and worktree after navigating up",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Force deletion even if marker exists or PR is open (prompts)",
)
@click.pass_obj
def up_cmd(ctx: ErkContext, count: int, script: bool, delete_current: bool, force: bool) -> None:
    """Move to child branch in worktree stack.

    Navigate up COUNT levels (default: 1).

    Navigate to target worktree:
      source <(erk up --script)
      source <(erk up 3 --script)

    Requires Graphite: 'erk config set use_graphite true'
    """
    execute_stack_navigation(
        ctx=ctx,
        direction="up",
        count=count,
        script=script,
        delete_current=delete_current,
        force=force,
    )
```

### 2. `src/erk/cli/commands/down.py`

Same change as `up.py` but for the down command.

```python
@click.command("down", cls=GraphiteCommandWithHiddenOptions)
@click.argument("count", type=int, default=1, required=False)
@script_option
@click.option(
    "--delete-current",
    is_flag=True,
    help="Delete current branch and worktree after navigating down",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Force deletion even if marker exists or PR is open (prompts)",
)
@click.pass_obj
def down_cmd(ctx: ErkContext, count: int, script: bool, delete_current: bool, force: bool) -> None:
    """Move to parent branch in worktree stack.

    Navigate down COUNT levels (default: 1).

    Navigate to target worktree:
      source <(erk down --script)
      source <(erk down 2 --script)

    Requires Graphite: 'erk config set use_graphite true'
    """
    execute_stack_navigation(
        ctx=ctx,
        direction="down",
        count=count,
        script=script,
        delete_current=delete_current,
        force=force,
    )
```

### 3. `src/erk/cli/commands/navigation_helpers.py`

This is the main change. Modify `execute_stack_navigation` to accept and handle the `count` parameter.

**Signature change** — add `count: int` parameter:

```python
def execute_stack_navigation(
    *,
    ctx: ErkContext,
    direction: Literal["up", "down"],
    count: int,
    script: bool,
    delete_current: bool,
    force: bool,
) -> NoReturn:
```

**Add validation** at the top of the function (after `Ensure.gh_authenticated`):

```python
Ensure.invariant(count >= 1, "Count must be at least 1")
Ensure.invariant(
    not (delete_current and count > 1),
    "Cannot use --delete-current with count > 1",
)
```

**Replace single resolution with loop** — instead of the current single call to `resolve_up_navigation` / `resolve_down_navigation`, loop N times. The key insight is that intermediate branches only need their target name resolved; the actual worktree path lookup and activation only happens for the **final** target.

Replace the current direction-specific resolution block (approximately lines 697-709) with:

```python
# Resolve navigation target by walking N steps in the given direction
target_name = current_branch
was_created = False

for step in range(count):
    if direction == "up":
        target_name, step_created = resolve_up_navigation(ctx, repo, target_name, worktrees)
        is_root = False
    else:  # direction == "down"
        target_name, step_created = resolve_down_navigation(
            ctx,
            repo=repo,
            current_branch=target_name,
            worktrees=worktrees,
            trunk_branch=ctx.trunk_branch,
        )
        is_root = target_name == "root"
        # Can't navigate further down from root
        if is_root and step < count - 1:
            user_output(
                click.style("Warning: ", fg="yellow")
                + f"Reached root after {step + 1} step(s) (requested {count})"
            )
            break

    # Track if any step created a worktree
    if step_created:
        was_created = True
```

Note: For `up` direction, `resolve_up_navigation` already handles the "multiple children" and "no children" error cases, so each step naturally validates. For `down`, reaching root before exhausting count emits a warning and stops (matching `gt down` behavior which stops at trunk).

**No other changes needed in this file** — the rest of the function (deletion prep, worktree path resolution, activation) already works on `target_name` and `is_root`, which are now set to the final destination after N steps.

### 4. `tests/commands/navigation/test_up.py`

Add tests for the count argument:

**`test_up_count_moves_multiple_levels`** — Set up a 4-branch stack (main -> f1 -> f2 -> f3), start at f1, run `erk up 2 --script`. Verify activation script targets f3.

**`test_up_count_1_is_default_behavior`** — Verify `erk up 1 --script` behaves identically to `erk up --script`.

**`test_up_count_zero_fails`** — Run `erk up 0 --script`, verify error exit with "Count must be at least 1" message.

**`test_up_count_exceeds_stack_fails`** — Set up main -> f1 -> f2, start at f1, run `erk up 3 --script`. Verify error about being at top of stack (the third step should fail with "no child branches").

**`test_up_count_with_delete_current_fails`** — Run `erk up 2 --delete-current --script`, verify error about incompatibility.

### 5. `tests/commands/navigation/test_down.py`

Add parallel tests for the count argument:

**`test_down_count_moves_multiple_levels`** — Set up a 4-branch stack (main -> f1 -> f2 -> f3), start at f3, run `erk down 2 --script`. Verify activation script targets f1.

**`test_down_count_1_is_default_behavior`** — Verify `erk down 1 --script` behaves identically to `erk down --script`.

**`test_down_count_zero_fails`** — Run `erk down 0 --script`, verify error exit.

**`test_down_count_to_root`** — Set up main -> f1 -> f2, start at f2, run `erk down 2 --script`. Since f2's parent is f1 and f1's parent is main (trunk/root), verify we navigate to root with a warning about reaching root.

**`test_down_count_exceeds_stack_stops_at_root`** — Set up main -> f1 -> f2, start at f2, run `erk down 10 --script`. Verify we navigate to root with a warning about reaching root after 2 steps.

**`test_down_count_with_delete_current_fails`** — Run `erk down 2 --delete-current --script`, verify error about incompatibility.

## Files NOT Changing

- **`packages/erk-shared/`** — No changes to BranchManager ABC, FakeGraphite, FakeGit, or any shared gateway code. The loop uses existing `get_parent_branch` / `get_child_branches` methods.
- **`src/erk/cli/cli.py`** — The commands are already registered; their signatures changing doesn't affect registration.
- **`src/erk/cli/commands/navigation_helpers.py` helper functions** — `resolve_up_navigation`, `resolve_down_navigation`, `activate_target`, `activate_worktree`, `activate_root_repo`, and all deletion-related functions remain unchanged. Only the `execute_stack_navigation` orchestrator changes.

## Verification

1. Run existing navigation tests to ensure no regressions: `pytest tests/commands/navigation/`
2. Run the new count-specific tests
3. Run type checker: `ty check src/erk/cli/commands/up.py src/erk/cli/commands/down.py src/erk/cli/commands/navigation_helpers.py`
4. Run linter: `ruff check src/erk/cli/commands/up.py src/erk/cli/commands/down.py src/erk/cli/commands/navigation_helpers.py`

## Edge Cases

- **count=1**: Identical to current behavior (backward compatible)
- **count > stack depth (up)**: `resolve_up_navigation` raises SystemExit with "no child branches" — correct behavior
- **count > stack depth (down)**: Stops at root with warning — matches gt behavior
- **Multiple children at any step (up)**: `resolve_up_navigation` already fails with "multiple children" error — correct behavior, no special handling needed
- **Auto-create worktrees**: `resolve_up_navigation` and `resolve_down_navigation` auto-create worktrees for intermediate and final branches as needed — this already works correctly in the loop