# Plan: `erk impl` should detect local `.erk/impl-context/`

## Context

When running `erk impl --dangerous` (no TARGET) on a plan branch that already has `.erk/impl-context/` set up, the command fails because `extract_plan_from_current_branch()` only checks the GitHub PR API. The `/erk:plan-implement` skill (via `erk exec setup-impl`) correctly handles this case by checking `.erk/impl-context/` first (Path 3a in `setup_impl.py:198-225`), but the `erk impl` CLI command does not.

## Change

Add `.erk/impl-context/` detection as a fallback in the no-target path. When impl-context already exists, skip straight to execution — no re-fetching from GitHub.

### File: `src/erk/cli/commands/implement.py`

**Add import** (line ~38):
```python
from erk_shared.impl_folder import resolve_impl_dir, read_plan_ref
```

**Replace the no-target block** (lines 390-406) with a three-strategy fallback:

```python
if target is None:
    # Strategy 1: Check existing .erk/impl-context/
    current_branch = ctx.git.branch.get_current_branch(ctx.cwd)
    impl_dir = resolve_impl_dir(ctx.cwd, branch_name=current_branch)
    if impl_dir is not None and (impl_dir / "plan.md").exists():
        user_output(f"Auto-detected impl-context at {impl_dir.relative_to(ctx.cwd)}")
        repo = discover_repo_context(ctx, ctx.cwd)
        # Skip straight to execution — impl is already set up
        _execute(
            ctx, repo=repo, dry_run=dry_run, submit=submit,
            dangerous=dangerous, script=script, no_interactive=no_interactive,
            verbose=verbose, model=model, executor=ctx.prompt_executor,
        )
        return

    # Strategy 2: Extract plan number from GitHub PR
    detected_plan = extract_plan_from_current_branch(ctx)
    if detected_plan is not None:
        target = detected_plan
        user_output(f"Auto-detected plan #{target} from branch")
    else:
        branch_display = current_branch or "unknown"
        raise click.ClickException(
            f"Could not auto-detect plan from branch '{branch_display}'.\n\n"
            f"No impl-context or plan PR found. Either:\n"
            f"  1. Provide TARGET explicitly: erk implement <TARGET>\n"
            f"  2. Switch to a plan branch: erk pr co <plan>\n"
            f"  3. Set up impl first: erk exec setup-impl --issue <plan>"
        )
```

**Extract execution logic into `_execute` helper** — pull the common execution dispatch (interactive/non-interactive/script) out of `_implement_from_issue` and `_implement_from_file` into a shared function:

```python
def _execute(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    script: bool,
    no_interactive: bool,
    verbose: bool,
    model: str | None,
    executor: PromptExecutor,
) -> None:
    """Execute implementation in current directory (impl-context must already exist)."""
    branch = ctx.git.branch.get_current_branch(ctx.cwd) or "current"

    if script:
        output_activation_instructions(
            ctx, wt_path=ctx.cwd, branch=branch, script=script,
            submit=submit, dangerous=dangerous, model=model,
            target_description="impl-context",
        )
    elif no_interactive:
        commands = build_command_sequence(submit)
        execute_non_interactive_mode(
            worktree_path=ctx.cwd, commands=commands, dangerous=dangerous,
            verbose=verbose, model=model, executor=executor,
        )
    else:
        execute_interactive_mode(
            ctx, repo_root=repo.root, worktree_path=ctx.cwd,
            dangerous=dangerous, model=model, executor=executor,
        )
```

Then refactor `_implement_from_issue` and `_implement_from_file` to call `_execute` after their setup phase, reducing duplication.

### Existing utilities reused
- `resolve_impl_dir` — `packages/erk-shared/src/erk_shared/impl_folder.py:54`
- `read_plan_ref` — `packages/erk-shared/src/erk_shared/impl_folder.py:301`
- `execute_interactive_mode` — `src/erk/cli/commands/implement_shared.py:250`
- `execute_non_interactive_mode` — `src/erk/cli/commands/implement_shared.py`
- `discover_repo_context` — already imported

## Verification

1. Run existing tests: `pytest tests/ -k implement`
2. Manual test on a plan branch with existing impl-context: `erk impl --dry-run` should detect it
3. Manual test with no impl-context and no PR: verify error message
4. Verify `erk impl 123` still works (explicit target path unchanged)
