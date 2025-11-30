# Plan: Auto-Close Orphaned Draft PRs on Plan Resubmit

## Problem

When a plan submission fails (workflow error) and the user resubmits with `erk submit`, a NEW draft PR is created because branch names include date suffixes (e.g., `impl-my-feature-25-11-29`). The old failed draft PR remains open and orphaned, cluttering the PR list.

## Solution

Automatically close old OPEN draft PRs linked to the same issue when a new draft PR is created during submission.

**Constraints (per user requirements):**

- Close during submission (not a separate cleanup command)
- Close the PR only (don't delete the branch) for reference

## Implementation

### Step 0: Add `labels` field to PullRequestInfo

The current `PullRequestInfo` dataclass doesn't have labels. We need to:

**File:** `packages/erk-shared/src/erk_shared/github/types.py`

Add to `PullRequestInfo`:

```python
labels: list[str] = field(default_factory=list)  # PR labels (e.g., ["erk-plan"])
```

**File:** `src/erk/core/github/real.py`

Update `_build_issue_pr_linkage_query()` GraphQL query to fetch labels:

```graphql
labels(first: 10) {
  nodes {
    name
  }
}
```

Update `_parse_issue_pr_linkages()` to extract labels from response.

### Step 1: Add `close_pr` to GitHub ABC Interface

**File:** `packages/erk-shared/src/erk_shared/github/abc.py`

Add after `create_pr()` method (line ~198):

```python
@abstractmethod
def close_pr(self, repo_root: Path, pr_number: int) -> None:
    """Close a pull request without deleting its branch.

    Args:
        repo_root: Repository root directory
        pr_number: PR number to close
    """
    ...
```

### Step 2: Implement in RealGitHub

**File:** `src/erk/core/github/real.py`

Add after `create_pr()` method:

```python
def close_pr(self, repo_root: Path, pr_number: int) -> None:
    """Close a pull request without deleting its branch."""
    cmd = ["gh", "pr", "close", str(pr_number)]
    execute_gh_command(cmd, repo_root)
```

### Step 3: Implement in FakeGitHub

**File:** `src/erk/core/github/fake.py`

Add tracking in `__init__`:

```python
self._closed_prs: list[int] = []
```

Add property and method:

```python
@property
def closed_prs(self) -> list[int]:
    """Read-only access to tracked PR closures for test assertions."""
    return self._closed_prs

def close_pr(self, repo_root: Path, pr_number: int) -> None:
    """Record PR closure in mutation tracking list."""
    self._closed_prs.append(pr_number)
```

### Step 4: Implement in DryRunGitHub

**File:** `src/erk/core/github/dry_run.py`

```python
def close_pr(self, repo_root: Path, pr_number: int) -> None:
    """No-op for dry-run mode."""
    pass
```

### Step 5: Implement in PrintingGitHub

**File:** `src/erk/core/github/printing.py`

```python
def close_pr(self, repo_root: Path, pr_number: int) -> None:
    """Close PR with printed output."""
    self._emit(self._format_command(f"gh pr close {pr_number}"))
    self._wrapped.close_pr(repo_root, pr_number)
```

### Step 6: Add stub to erk-shared RealGitHub

**File:** `packages/erk-shared/src/erk_shared/github/real.py`

```python
def close_pr(self, repo_root: Path, pr_number: int) -> None:
    """Stub method - not implemented in erk-shared."""
    msg = (
        "RealGitHub from erk-shared is a stub for context creation only. "
        "Use the full implementation from erk.core.github.real."
    )
    raise NotImplementedError(msg)
```

### Step 7: Add orphan closing logic to submit.py

**File:** `src/erk/cli/commands/submit.py`

Add helper function (after `_construct_pr_url()`):

```python
def _close_orphaned_draft_prs(
    ctx: ErkContext,
    repo_root: Path,
    issue_number: int,
    keep_pr_number: int,
) -> list[int]:
    """Close old draft PRs linked to an issue, keeping the specified one.

    Returns list of PR numbers that were closed.
    """
    pr_linkages = ctx.github.get_prs_linked_to_issues(repo_root, [issue_number])
    linked_prs = pr_linkages.get(issue_number, [])

    closed_prs: list[int] = []
    for pr in linked_prs:
        # Close only: draft PRs with erk-plan label, that are OPEN, and not the one we just created
        is_erk_plan_pr = "erk-plan" in pr.labels
        if pr.is_draft and pr.state == "OPEN" and pr.number != keep_pr_number and is_erk_plan_pr:
            ctx.github.close_pr(repo_root, pr.number)
            closed_prs.append(pr.number)

    return closed_prs
```

In `submit_cmd()`, after `ctx.github.update_pr_body(...)` (line ~236), add:

```python
# Close any orphaned draft PRs from previous failed submissions
closed_prs = _close_orphaned_draft_prs(ctx, repo.root, issue_number, pr_number)
if closed_prs:
    closed_str = ", ".join(f"#{n}" for n in closed_prs)
    user_output(
        click.style("✓", fg="green")
        + f" Closed {len(closed_prs)} orphaned draft PR(s): {closed_str}"
    )
```

### Step 8: Update Documentation

**File:** `docs/agent/plan-lifecycle.md`

Add new section after "### Draft PR Creation" (around line 199):

```markdown
### Orphaned Draft PR Cleanup

When resubmitting a plan (e.g., after a failed workflow), branch names change due to date suffixes. This creates a new draft PR while leaving the old one orphaned.

**Automatic cleanup**: After creating a new draft PR, `erk submit` automatically closes any orphaned draft PRs linked to the same issue.

**Closure criteria** (all must be true):

- PR is a draft (`is_draft == True`)
- PR is open (`state == "OPEN"`)
- PR has the `erk-plan` label
- PR is not the newly created one

**Branches preserved**: Only the PR is closed; the branch remains for reference.

**Output**: Users see a confirmation message listing closed PRs:
```

✓ Closed 1 orphaned draft PR(s): #456

```

```

### Step 9: Add Unit Tests

**File:** `tests/commands/test_submit.py`

Test cases:

1. `test_submit_closes_orphaned_draft_prs` - Verify old drafts with erk-plan label are closed
2. `test_submit_skips_non_draft_prs` - Ready-for-review PRs not closed
3. `test_submit_skips_closed_prs` - Already closed PRs not touched
4. `test_submit_skips_merged_prs` - Merged PRs not touched
5. `test_submit_does_not_close_newly_created_pr` - New PR excluded
6. `test_submit_skips_prs_without_erk_plan_label` - PRs without erk-plan label not touched

## Critical Files

| File                                                 | Change                                                            |
| ---------------------------------------------------- | ----------------------------------------------------------------- |
| `packages/erk-shared/src/erk_shared/github/types.py` | Add `labels` field to `PullRequestInfo`                           |
| `packages/erk-shared/src/erk_shared/github/abc.py`   | Add `close_pr` abstract method                                    |
| `src/erk/core/github/real.py`                        | Implement `close_pr`, update GraphQL query + parser for labels    |
| `src/erk/core/github/fake.py`                        | Add tracking for tests                                            |
| `src/erk/core/github/dry_run.py`                     | No-op implementation                                              |
| `src/erk/core/github/printing.py`                    | Printing wrapper                                                  |
| `packages/erk-shared/src/erk_shared/github/real.py`  | Stub implementation                                               |
| `src/erk/cli/commands/submit.py`                     | Add helper and call after PR creation                             |
| `tests/commands/test_submit.py`                      | Unit tests                                                        |
| `docs/agent/plan-lifecycle.md`                       | Add "Orphaned Draft PR Cleanup" section after "Draft PR Creation" |

## Filter Logic

Only close PRs that match ALL of:

- `is_draft == True` (only drafts, not ready-for-review)
- `state == "OPEN"` (not already closed/merged)
- `number != keep_pr_number` (not the one we just created)
- Has `erk-plan` label (only erk-created PRs, not arbitrary PRs referencing the issue)

This is conservative - preserves any non-draft PRs or manually created PRs that happen to reference the issue.
