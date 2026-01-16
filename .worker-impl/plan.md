# Plan: `erk plan co` Command

## Overview

Add `erk plan co <plan_id>` command to checkout the branch associated with a plan.

## Behavior

1. **Local branch exists** → Check it out (create worktree if needed)
2. **No local branch, single open PR** → Checkout the PR branch
3. **Multiple local branches or PRs** → Display table, exit with code 1
4. **Neither exists** → Politely inform user, exit with code 1

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/erk/cli/commands/plan/checkout_cmd.py` | Create (new command) |
| `src/erk/cli/commands/plan/__init__.py` | Modify (register command) |
| `tests/unit/cli/commands/plan/test_checkout_cmd.py` | Create (unit tests) |

## Implementation

### 1. Create `checkout_cmd.py`

```python
# src/erk/cli/commands/plan/checkout_cmd.py

@alias("co")
@click.command("checkout", cls=CommandWithHiddenOptions)
@click.argument("plan_id", type=str)
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@script_option
@click.pass_obj
def plan_checkout(ctx: ErkContext, plan_id: str, force: bool, script: bool) -> None:
    """Checkout the branch associated with a plan."""
```

### 2. Algorithm

```
1. Parse plan_id → issue_number (via parse_issue_identifier)
2. Fetch plan → get issue body
3. Extract worktree_name from plan-header metadata
4. Find local branches matching pattern P{issue_number}-*
   - Also include worktree_name if set and not already matched
5. Get linked PRs via ctx.issues.get_prs_referencing_issue()
   - Filter to OPEN PRs only

Decision tree:
- 1 local branch → checkout via allocate_slot_for_branch + navigate_to_worktree
- Multiple local branches → display list, suggest "erk br co <branch>"
- 0 local branches + 1 open PR → fetch PR branch via get_pr(), checkout
- 0 local branches + multiple open PRs → display table, suggest "erk pr co <pr>"
- 0 local branches + 0 open PRs → inform user, suggest "erk plan implement"
```

### 3. Key Functions to Reuse

| Function | From | Purpose |
|----------|------|---------|
| `parse_issue_identifier` | `erk.cli.github_parsing` | Parse plan ID |
| `extract_plan_header_worktree_name` | `erk_shared.github.metadata.plan_header` | Get branch from metadata |
| `allocate_slot_for_branch` | `erk.cli.commands.slot.common` | Create worktree for branch |
| `navigate_to_worktree` | `erk.cli.commands.checkout_helpers` | Shell integration |
| `ctx.issues.get_prs_referencing_issue` | Issues gateway | Get linked PRs |
| `ctx.github.get_pr` | GitHub gateway | Get full PR details (for branch name) |

### 4. Table Format for Multiple PRs

```
Plan #123 has multiple open PRs:

PR       State   Branch                Title
#456     OPEN    P123-first-attempt    Initial implementation
#789     DRAFT   P123-second-try       Alternative approach

Checkout a specific PR with: erk pr co <pr_number>
```

### 5. Register Command

In `src/erk/cli/commands/plan/__init__.py`:
```python
from erk.cli.commands.plan.checkout_cmd import plan_checkout
# ...
plan_group.add_command(plan_checkout)
```

## Testing

Tests in `tests/unit/cli/commands/plan/test_checkout_cmd.py`:

1. **test_checkout_local_branch_exists** - Single matching branch → checkout succeeds
2. **test_checkout_multiple_local_branches** - Multiple branches → table displayed, exits 1
3. **test_checkout_no_branch_single_pr** - No branch, one open PR → PR checked out
4. **test_checkout_no_branch_multiple_prs** - No branch, multiple PRs → table displayed, exits 1
5. **test_checkout_no_branch_no_pr** - Neither exists → informative message, exits 1
6. **test_checkout_worktree_name_from_metadata** - Uses worktree_name field from plan header
7. **test_checkout_plan_not_found** - Invalid plan ID → error message

Use `FakeGit`, `FakeGitHub`, `FakeGitHubIssues` from fake-driven testing architecture.

## Verification

1. Run `make fast-ci` to verify tests pass
2. Manual testing:
   - `erk plan co <existing-plan-with-branch>` → should checkout
   - `erk plan co <plan-with-pr-but-no-local>` → should checkout PR
   - `erk plan co <plan-with-multiple-prs>` → should show table
   - `erk plan co <plan-with-nothing>` → should show helpful message