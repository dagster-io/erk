# Plan: Address PR Review Comments for #5609 (Round 2)

## Summary

Address 3 review comments requesting `erk exec` commands instead of raw `gh api` calls. All three can be addressed using **existing gateway methods** - no new exec commands are required.

## Analysis

### Review Comments

| Thread ID | Line | Current Code | Request |
|-----------|------|--------------|---------|
| PRRT_kwDOPxC3hc5qo--5 | 37 | `gh api .../issues/<NUMBER> --jq '.labels[].name' \| grep -q "erk-plan"` | Make this an erk exec command |
| PRRT_kwDOPxC3hc5qo-bp | 128 | `gh pr view <NUMBER> --json commits --jq '.commits[].oid'` | Make this an erk exec command |
| PRRT_kwDOPxC3hc5qo_S6 | 261 | `gh api .../comments -X POST` + `gh api ... -X PATCH -f state=closed` | Make this an erk exec command |

### Solution Approach

**Key Insight:** The existing `erk exec get-issue-body` command already returns `labels` in its JSON output. For the other operations, we can create minimal new exec commands or use existing gateway methods.

**Comment 1 (line 37):** Replace with `erk exec get-issue-body <NUMBER>` and check if `"erk-plan"` is in the returned `labels` array. No new exec command needed.

**Comment 2 (line 128):** This uses `gh pr view --json commits` which uses GraphQL. Need a new exec command `get-pr-commits` that uses REST API.

**Comment 3 (line 261):** Need a new exec command `close-issue-with-comment` that combines `add_comment()` + `close_issue()` gateway methods.

## Execution Plan

### Batch 1: Documentation-Only Fix (line 37)

Replace raw `gh api` call with existing `erk exec get-issue-body`:

**Old (line 33-37):**
```bash
gh api repos/dagster-io/erk/issues/<NUMBER> --jq '.labels[].name' | grep -q "erk-plan" && echo "plan" || echo "pr"
```

**New:**
```bash
erk exec get-issue-body <NUMBER> | jq -e '.labels | index("erk-plan")' > /dev/null && echo "plan" || echo "pr"
```

### Batch 2: New Exec Command (line 128)

Create `get-pr-commits` exec command:

**Files to create:**
- `src/erk/cli/commands/exec/scripts/get_pr_commits.py`
- `tests/unit/cli/commands/exec/scripts/test_get_pr_commits.py`

**File to modify:**
- `src/erk/cli/commands/exec/group.py` (add import and registration)

**Gateway consideration:** The GitHub ABC doesn't have a `get_pr_commits` method. Options:
1. Add method to GitHub ABC (requires 5 implementations: abc, real, fake, dry_run, printing)
2. Use `gh api` REST call directly in the exec script (simpler, acceptable for read-only)

Recommend option 2 for simplicity - exec script can call `gh api repos/{owner}/{repo}/pulls/{number}/commits` directly since this is read-only.

**Update command documentation (line 125-128):**

**Old:**
```bash
gh pr view <NUMBER> --json commits --jq '.commits[].oid' | while read sha; do
  git branch --contains "$sha" 2>/dev/null | grep -qE '^\*?\s*master$' && echo "$sha: IN_MASTER" || echo "$sha: NOT_IN_MASTER"
done
```

**New:**
```bash
erk exec get-pr-commits <NUMBER> | jq -r '.commits[].sha' | while read sha; do
  git branch --contains "$sha" 2>/dev/null | grep -qE '^\*?\s*master$' && echo "$sha: IN_MASTER" || echo "$sha: NOT_IN_MASTER"
done
```

### Batch 3: New Exec Command (line 261)

Create `close-issue-with-comment` exec command:

**Files to create:**
- `src/erk/cli/commands/exec/scripts/close_issue_with_comment.py`
- `tests/unit/cli/commands/exec/scripts/test_close_issue_with_comment.py`

**File to modify:**
- `src/erk/cli/commands/exec/group.py` (add import and registration)

**Implementation:** Uses existing gateway methods `add_comment()` then `close_issue()`.

**Update command documentation (line 258-261):**

**Old:**
```bash
gh api repos/dagster-io/erk/issues/<NUMBER>/comments -X POST -f body="Closing: ..."
gh api repos/dagster-io/erk/issues/<NUMBER> -X PATCH -f state=closed
```

**New:**
```bash
erk exec close-issue-with-comment <NUMBER> --comment "Closing: This work is already represented in master. <evidence>"
```

## Implementation Steps

### Step 1: Create `get-pr-commits` exec command

```python
# src/erk/cli/commands/exec/scripts/get_pr_commits.py
"""Get commits for a PR using REST API.

Usage:
    erk exec get-pr-commits <PR_NUMBER>

Output:
    JSON with {success, pr_number, commits: [{sha, message, author}]}
"""

import json
import subprocess

import click

from erk_shared.context.helpers import require_repo_root


@click.command(name="get-pr-commits")
@click.argument("pr_number", type=int)
@click.pass_context
def get_pr_commits(ctx: click.Context, pr_number: int) -> None:
    """Get commits for a PR using REST API."""
    repo_root = require_repo_root(ctx)

    result = subprocess.run(
        ["gh", "api", f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/commits", "--jq", "..."],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    # ... parse and output JSON
```

### Step 2: Create `close-issue-with-comment` exec command

```python
# src/erk/cli/commands/exec/scripts/close_issue_with_comment.py
"""Close an issue with a comment using REST API.

Usage:
    erk exec close-issue-with-comment <ISSUE_NUMBER> --comment "message"

Output:
    JSON with {success, issue_number, comment_id}
"""

import json

import click

from erk_shared.context.helpers import require_issues, require_repo_root


@click.command(name="close-issue-with-comment")
@click.argument("issue_number", type=int)
@click.option("--comment", required=True, help="Comment to add before closing")
@click.pass_context
def close_issue_with_comment(ctx: click.Context, issue_number: int, *, comment: str) -> None:
    """Close an issue with a comment."""
    github = require_issues(ctx)
    repo_root = require_repo_root(ctx)

    comment_id = github.add_comment(repo_root, issue_number, comment)
    github.close_issue(repo_root, issue_number)

    click.echo(json.dumps({
        "success": True,
        "issue_number": issue_number,
        "comment_id": comment_id,
    }))
```

### Step 3: Register commands in group.py

Add imports and registrations for both new commands.

### Step 4: Update check-relevance.md

Update lines 33-37, 125-128, and 258-261 with the new `erk exec` commands.

### Step 5: Write tests

Create unit tests for both new exec commands using `FakeGitHubIssues`.

### Step 6: Run CI and commit

### Step 7: Resolve threads

Resolve all 3 threads with appropriate comments.

## Verification

1. Run `make fast-ci` to verify tests pass
2. Manually test each new exec command:
   - `erk exec get-pr-commits 5609`
   - `erk exec close-issue-with-comment <test-issue> --comment "test"` (on a test issue)
3. Re-fetch review comments to confirm all threads resolved

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/get_pr_commits.py` | Create new |
| `src/erk/cli/commands/exec/scripts/close_issue_with_comment.py` | Create new |
| `src/erk/cli/commands/exec/group.py` | Add 2 imports + registrations |
| `tests/unit/cli/commands/exec/scripts/test_get_pr_commits.py` | Create new |
| `tests/unit/cli/commands/exec/scripts/test_close_issue_with_comment.py` | Create new |
| `.claude/commands/local/check-relevance.md` | Update 3 code blocks |

## Related Documentation

- `docs/learned/architecture/github-api-rate-limits.md` - REST API guidance
- `src/erk/cli/commands/exec/scripts/AGENTS.md` - Exec script standards