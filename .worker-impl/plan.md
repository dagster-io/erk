# Plan: Detect and Reuse Existing Local Branches in Plan Submit

## Problem

When running `erk plan submit`, the command always computes a new branch name with the current timestamp, even if a local branch for the same issue already exists. This leaves orphan branches and breaks Graphite tracking.

Example:
- User has local branch `P5673-add-documentation-to-pr-5-01-23-0909`
- Running `plan submit 5673` creates NEW branch `P5673-add-documentation-to-pr-5-01-23-0910`
- Original branch `0909` is left untracked and orphaned

## Solution

Detect existing local branches matching `P{issue_number}-*` pattern BEFORE computing a new branch name. Prompt user to choose:
1. **Use existing branch** - Track it in Graphite and proceed with submission
2. **Delete and create new** - Remove existing branch(es), create fresh one
3. **Abort** - Cancel the operation

## Implementation

### File to Modify

**`src/erk/cli/commands/submit.py`**

### Changes

#### 1. Add helper: detect existing branches (after line 93)

```python
def _find_existing_branches_for_issue(
    ctx: ErkContext,
    repo_root: Path,
    issue_number: int,
) -> list[str]:
    """Find local branches matching P{issue_number}-* pattern."""
    local_branches = ctx.git.list_local_branches(repo_root)
    prefix = f"P{issue_number}-"
    return sorted([b for b in local_branches if b.startswith(prefix)])
```

#### 2. Add helper: prompt user (after previous helper)

```python
def _prompt_existing_branch_action(
    ctx: ErkContext,
    repo_root: Path,
    existing_branches: list[str],
    new_branch_name: str,
) -> str | None:
    """Prompt user to decide what to do with existing branch(es).

    Returns:
        - Branch name to use (existing branch)
        - None to signal "create new" (after deleting existing)

    Raises:
        SystemExit: If user aborts
    """
    user_output(f"\nFound existing local branch(es) for this issue:")
    for branch in existing_branches:
        user_output(f"  • {branch}")
    user_output(f"\nNew branch would be: {click.style(new_branch_name, fg='cyan')}")
    user_output("")

    # Use newest branch (latest timestamp = last alphabetically)
    branch_to_use = existing_branches[-1]
    if ctx.console.confirm(f"Use existing branch '{branch_to_use}'?", default=True):
        return branch_to_use

    if ctx.console.confirm("Delete existing branch(es) and create new?", default=False):
        for branch in existing_branches:
            ctx.branch_manager.delete_branch(repo_root, branch, force=True)
            user_output(f"Deleted branch: {branch}")
        return None

    user_output(click.style("Aborted.", fg="red"))
    raise SystemExit(1)
```

#### 3. Modify `_validate_issue_for_submit` (lines 295-306)

Replace:
```python
    # Compute branch name: P prefix + issue number + sanitized title + timestamp
    # Apply P prefix AFTER sanitization since sanitize_worktree_name lowercases input
    # Truncate total to 31 chars before adding timestamp suffix
    prefix = f"P{issue_number}-"
    sanitized_title = sanitize_worktree_name(issue.title)
    base_branch_name = (prefix + sanitized_title)[:31].rstrip("-")
    logger.debug("base_branch_name=%s", base_branch_name)
    timestamp_suffix = format_branch_timestamp_suffix(ctx.time.now())
    logger.debug("timestamp_suffix=%s", timestamp_suffix)
    branch_name = base_branch_name + timestamp_suffix
    logger.debug("branch_name=%s", branch_name)
    user_output(f"Computed branch: {click.style(branch_name, fg='cyan')}")
```

With:
```python
    # Check for existing local branches BEFORE computing new name
    existing_branches = _find_existing_branches_for_issue(ctx, repo.root, issue_number)

    # Compute branch name components (needed for both paths)
    prefix = f"P{issue_number}-"
    sanitized_title = sanitize_worktree_name(issue.title)
    base_branch_name = (prefix + sanitized_title)[:31].rstrip("-")
    timestamp_suffix = format_branch_timestamp_suffix(ctx.time.now())
    new_branch_name = base_branch_name + timestamp_suffix

    if existing_branches:
        chosen = _prompt_existing_branch_action(ctx, repo.root, existing_branches, new_branch_name)
        branch_name = chosen if chosen is not None else new_branch_name
    else:
        branch_name = new_branch_name

    logger.debug("branch_name=%s", branch_name)
    user_output(f"Computed branch: {click.style(branch_name, fg='cyan')}")
```

#### 4. Modify `_submit_single_issue` else branch (lines 561-598)

Replace:
```python
    else:
        # Create branch and initial commit
        user_output(f"Creating branch from origin/{base_branch}...")

        # Fetch base branch
        ctx.git.fetch_branch(repo.root, "origin", base_branch)

        # Before creating the stacked branch, verify parent is tracked by Graphite (if enabled)
        ...
        ctx.branch_manager.create_branch(repo.root, branch_name, f"origin/{base_branch}")
        user_output(f"Created branch: {click.style(branch_name, fg='cyan')}")

        # Use context manager to restore original branch on failure
        with branch_rollback(ctx, repo.root, original_branch):
            pr_number = _create_branch_and_pr(...)
```

With:
```python
    else:
        # Check if branch exists locally (user chose to reuse existing)
        local_branches = ctx.git.list_local_branches(repo.root)
        branch_exists_locally = branch_name in local_branches

        if branch_exists_locally:
            # Reuse existing local branch
            user_output(f"Using existing local branch: {click.style(branch_name, fg='cyan')}")

            # Track in Graphite if not already tracked
            if ctx.branch_manager.is_graphite_managed():
                if not ctx.graphite.is_branch_tracked(repo.root, branch_name):
                    ctx.graphite.track_branch(repo.root, branch_name, base_branch)
                    user_output(click.style("✓", fg="green") + " Branch tracked in Graphite")

            # Checkout existing branch
            ctx.branch_manager.checkout_branch(repo.root, branch_name)
        else:
            # Create new branch
            user_output(f"Creating branch from origin/{base_branch}...")
            ctx.git.fetch_branch(repo.root, "origin", base_branch)

            # Verify parent is tracked by Graphite (if enabled)
            if ctx.branch_manager.is_graphite_managed():
                parent_branch = base_branch.removeprefix("origin/")
                if not ctx.graphite.is_branch_tracked(repo.root, parent_branch):
                    msg = (
                        f"Cannot stack on branch '{parent_branch}' - it's not tracked by Graphite.\n\n"
                        f"To fix this:\n"
                        f"  1. gt checkout {parent_branch}\n"
                        f"  2. gt track --parent <parent-branch>\n\n"
                        f"Then retry your command."
                    )
                    user_output(click.style("Error: ", fg="red") + msg)
                    raise SystemExit(1)

            ctx.branch_manager.create_branch(repo.root, branch_name, f"origin/{base_branch}")
            user_output(f"Created branch: {click.style(branch_name, fg='cyan')}")

        # Use context manager to restore original branch on failure
        with branch_rollback(ctx, repo.root, original_branch):
            pr_number = _create_branch_and_pr(
                ctx=ctx,
                repo=repo,
                validated=validated,
                branch_name=branch_name,
                base_branch=base_branch,
                submitted_by=submitted_by,
                original_branch=original_branch,
            )
```

### Tests

Add to `tests/commands/submit/test_existing_branch_detection.py`:

1. **test_detects_existing_branch** - Verify detection of `P{N}-*` branches
2. **test_use_existing_branch** - User confirms "use existing", branch is tracked in Graphite
3. **test_delete_and_create_new** - User chooses delete, old branches removed, new created
4. **test_abort_on_existing** - User declines both options, exits with code 1
5. **test_multiple_existing_branches** - Uses newest (last alphabetically)

## Verification

1. Create a local branch: `git checkout -b P9999-test-01-23-0909 master`
2. Run `erk plan submit 9999` (with valid erk-plan issue)
3. Verify prompt appears
4. Test each path (use existing, delete, abort)
5. Check Graphite tracking: `gt ls`