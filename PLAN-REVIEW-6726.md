# Plan: Simplify branch reuse prompt in `erk plan submit`

## Goal

Replace the two sequential yes/no prompts with a single binary choice when existing branches are found.

## Current behavior (lines 144-162 in `submit.py`)

```
Found existing local branch(es) for this issue:
  • P6699-erk-plan-audit-phase-1-do-02-04-0842

New branch would be: P6699-erk-plan-audit-phase-1-do-02-04-1520

Use existing branch 'P6699-...-0842'? [Y/n]: n
Delete existing branch(es) and create new? [y/N]: y
```

Two separate `ctx.console.confirm()` calls. Saying "no" to the first leads to a second prompt. Saying "no" to both aborts.

## New behavior

```
Found existing local branch(es) for this issue:
  • P6699-erk-plan-audit-phase-1-do-02-04-0842

New branch would be: P6699-erk-plan-audit-phase-1-do-02-04-1520

Reuse existing branch? If not, a new branch and PR will be created (old draft PR will be closed). [Y/n]:
```

Single `confirm()` call:
- **Yes** (default) → reuse the existing branch (same as current "use existing" path; will reuse existing PR if one exists on remote)
- **No** → delete existing branch(es) and create new (same as current "delete and create" path; creates new PR, closes old orphaned draft PRs)

No abort path — it's a binary choice. If the user wants to abort they can Ctrl+C.

## PR consequence accuracy

Based on code analysis:
- **Reuse existing branch**: If branch exists on remote with a PR, that PR is reused directly (line 578-583). If branch is local-only or remote without PR, a new PR is created anyway.
- **Delete & create new**: Always creates a fresh branch + new draft PR. Old orphaned draft PRs are closed via `_close_orphaned_draft_prs()`.

So the messaging "a new branch and PR will be created (old draft PR will be closed)" is accurate for the typical case.

## Files to modify

### 1. `src/erk/cli/commands/submit.py` — `_prompt_existing_branch_action()` (lines 113-162)

Replace the two-prompt logic with:

```python
def _prompt_existing_branch_action(
    ctx: ErkContext,
    repo_root: Path,
    existing_branches: list[str],
    new_branch_name: str,
    *,
    force: bool,
) -> str | None:
    # force mode unchanged (lines 137-142)
    if force:
        user_output(f"\nDeleting {len(existing_branches)} existing branch(es) (--force mode):")
        for branch in existing_branches:
            ctx.branch_manager.delete_branch(repo_root, branch, force=True)
            user_output(f"  Deleted: {branch}")
        return None

    user_output("\nFound existing local branch(es) for this issue:")
    for branch in existing_branches:
        user_output(f"  • {branch}")
    user_output(f"\nNew branch would be: {click.style(new_branch_name, fg='cyan')}")
    user_output("")

    branch_to_use = existing_branches[-1]

    # Single binary prompt
    reuse = ctx.console.confirm(
        f"Reuse existing branch '{branch_to_use}'? "
        "If not, a new branch and PR will be created (old draft PR will be closed)",
        default=True,
    )

    if reuse:
        return branch_to_use

    # Delete existing branches and signal "create new"
    for branch in existing_branches:
        ctx.branch_manager.delete_branch(repo_root, branch, force=True)
        user_output(f"Deleted branch: {branch}")
    return None
```

Key changes:
- Remove second `confirm()` call
- Remove abort/`SystemExit(1)` path
- Add consequence messaging to the single prompt
- Docstring updated: remove "Raises: SystemExit" since no abort path

### 2. `docs/learned/planning/submit-branch-reuse.md`

Update the "User Workflow" section to reflect the new single-prompt UX (2 paths instead of 3, remove "Abort" option).

### 3. `tests/commands/plan/test_submit.py`

Add tests for the new prompt behavior:
- Test reuse path (confirm=True)
- Test delete-and-create path (confirm=False)
- Verify force mode still works (no prompt)

## Verification

1. Run `devrun` agent with `uv run pytest tests/commands/plan/test_submit.py`
2. Manual test: `erk plan submit <issue>` with an existing branch to verify the new prompt