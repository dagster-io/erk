# Plan: Change `erk pr rebase` to use `gt restack` / `git rebase` with Claude TUI fallback

## Context

Currently `erk pr rebase` invokes Claude as a subprocess (`--print` mode with `stream_rebase()`) to handle rebasing non-interactively. The user wants a two-phase approach instead:

1. **Phase 1 — Attempt the rebase mechanically** via `gt restack` (Graphite on) or `git rebase <target>` (Graphite off)
2. **Phase 2 — If conflicts arise**, launch Claude TUI interactively with `/erk:rebase` so the user can collaborate on resolution in real-time

Key decisions from user:
- Graphite ON + branch not tracked = **error** (not a fallback to git rebase)
- Graphite OFF = take a `--target` argument for `git rebase <target>`
- On success (no conflicts) = print success and exit (no auto-push)
- On conflict = leave rebase paused, launch Claude TUI

## File to Modify

### `src/erk/cli/commands/pr/rebase_cmd.py`

**New flow:**

```python
@click.command("rebase")
@click.option("-d", "--dangerous", is_flag=True, ...)
@click.option("--target", default=None, help="Target branch for git rebase (non-Graphite only)")
@click.pass_obj
def rebase(ctx: ErkContext, *, dangerous: bool, target: str | None) -> None:
    Ensure.dangerous_flag(ctx, dangerous=dangerous)
    cwd = ctx.cwd
    executor = ctx.prompt_executor
    Ensure.invariant(executor.is_available(), "Claude CLI required...")

    graphite_enabled = _is_graphite_enabled(ctx)

    if graphite_enabled:
        # Graphite path: gt restack
        branch = ctx.git.branch.get_current_branch(cwd)
        Ensure.invariant(
            branch is not None and ctx.graphite.is_branch_tracked(ctx.repo_root, branch),
            "Current branch is not tracked by Graphite. Track it with: gt track",
        )
        click.echo(click.style("Restacking with Graphite...", fg="yellow"))
        result = subprocess.run(
            ["gt", "restack", "--no-interactive"],
            cwd=cwd, capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            click.echo(click.style("Restack complete!", fg="green", bold=True))
            return
        # Check if conflicts left rebase in progress
        if not ctx.git.rebase.is_rebase_in_progress(cwd):
            raise click.ClickException(f"gt restack failed:\n{result.stderr}")
        click.echo(click.style("Restack hit conflicts. Launching Claude...", fg="yellow"))
    else:
        # Non-Graphite path: git rebase <target>
        if not ctx.git.rebase.is_rebase_in_progress(cwd):
            # Need a target to start a fresh rebase
            Ensure.invariant(
                target is not None,
                "Specify --target <branch> for git rebase (Graphite is not enabled)",
            )
            click.echo(click.style(f"Rebasing onto {target}...", fg="yellow"))
            rebase_result = ctx.git.rebase.rebase_onto(cwd, target)
            if rebase_result.success:
                click.echo(click.style("Rebase complete!", fg="green", bold=True))
                return
            click.echo(click.style("Rebase hit conflicts. Launching Claude...", fg="yellow"))
        else:
            click.echo(click.style("Rebase in progress. Launching Claude...", fg="yellow"))

    # Both paths converge here: conflicts exist, launch Claude TUI
    click.echo("Launching Claude...", err=True)
    executor.execute_interactive(
        worktree_path=cwd,
        dangerous=dangerous,
        command="/erk:rebase",
        target_subpath=None,
        model=None,
        permission_mode="edits",
    )
    # Never returns — process replaced by os.execvp
```

**Helper** (inline in the file, same pattern as `ErkContext.branch_manager`):

```python
def _is_graphite_enabled(ctx: ErkContext) -> bool:
    graphite = ctx.graphite
    if isinstance(graphite, DryRunGraphite):
        graphite = graphite._wrapped
    return not isinstance(graphite, GraphiteDisabled)
```

**Imports to add:** `subprocess`, `GraphiteDisabled`, `DryRunGraphite`
**Imports to remove:** `from erk.cli.output import stream_rebase`
**Code to remove:** The `stream_rebase` call and its `requires_interactive` / `error_message` result handling

### No other files need changes

- `stream_rebase` in `output.py` stays (used by remote rebase workflow)
- `/erk:rebase` command (`rebase.md`) stays as-is — it already handles picking up a paused rebase

## Existing code reused

| Function | Location |
|---|---|
| `ctx.graphite.is_branch_tracked()` | `packages/erk-shared/.../graphite/abc.py:250` |
| `ctx.git.branch.get_current_branch()` | `packages/erk-shared/.../git/branch_ops/abc.py:93` |
| `ctx.git.rebase.is_rebase_in_progress()` | `packages/erk-shared/.../git/rebase_ops/abc.py:77` |
| `ctx.git.rebase.rebase_onto()` | `packages/erk-shared/.../git/rebase_ops/abc.py:29` |
| `executor.execute_interactive()` | `src/erk/core/prompt_executor.py:463` |
| `GraphiteDisabled` check pattern | `packages/erk-shared/.../context/context.py:184-188` |

## Verification

1. **Graphite ON, no conflicts**: `erk pr rebase -d` → runs `gt restack`, prints success
2. **Graphite ON, with conflicts**: `gt restack` fails → detects rebase-in-progress → launches Claude TUI with `/erk:rebase`
3. **Graphite ON, branch not tracked**: error message telling user to `gt track`
4. **Graphite OFF, fresh rebase**: `erk pr rebase -d --target main` → runs `git rebase main` → succeeds or launches Claude TUI
5. **Graphite OFF, no target, no in-progress rebase**: error asking for `--target`
6. **Rebase already in progress** (either path): skips mechanical rebase, launches Claude TUI directly
7. Run `pytest tests/unit/cli/commands/pr/` for existing test coverage
