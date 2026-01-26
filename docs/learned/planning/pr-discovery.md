---
title: PR Discovery Fallback Strategies
read_when:
  - "implementing erk learn workflow"
  - "discovering PRs when branch_name is missing"
  - "debugging PR discovery failures"
  - "working with session metadata"
---

# PR Discovery Fallback Strategies

When implementing `erk learn`, agents need to find the PR associated with a plan's implementation. This requires fallback strategies when `branch_name` is missing from session metadata.

## The Challenge

Session metadata stored in `.erk/scratch/session-registry/` may have incomplete information:

```json
{
  "session_id": "abc123",
  "issue_number": 1234,
  "branch_name": null,  // ← Missing!
  "pr_number": null,
  "start_time": "2024-01-15T10:00:00Z"
}
```

Without `branch_name`, the agent cannot use `gh pr list --head <branch>` to find the PR.

## Primary Strategy: Use Issue Number

**Best approach:** If the PR description contains "Closes #1234", use GitHub's issue timeline:

```bash
gh api "/repos/{owner}/{repo}/issues/${ISSUE_NUMBER}/timeline" \
  --jq '.[] | select(.event == "cross-referenced") | .source.issue.number'
```

This finds PRs that reference the issue.

**Limitation:** Only works if PR description includes "Closes #XXXX" or similar keywords.

## Fallback Strategy: Git History Investigation

When issue-based discovery fails, investigate git history:

### Step 1: Search Commit Messages

```bash
git log --all --grep="erk-plan #${ISSUE_NUMBER}" --format="%H %s"
```

Erk implementation sessions often include issue numbers in commit messages.

### Step 2: Find Branch for Commit

Once you have a commit hash:

```bash
git branch --contains <commit-hash> --all
```

Filter to find the feature branch (exclude master/main).

### Step 3: Find PR for Branch

```bash
gh pr list --head <branch-name> --state all --json number,state
```

### Step 4: Validate PR Content

Verify the PR actually addresses the plan by checking:

- PR description mentions issue number
- File changes match plan scope
- PR was created after plan creation

## When Both Strategies Fail

If neither strategy finds a PR:

1. **Check PR state** - May be draft or closed without merge
2. **Check branch naming** - May not follow erk conventions
3. **Manual investigation** - User may need to provide PR number

**Output guidance:** Document the investigation steps taken and suggest manual intervention.

## Implementation Pattern

See `src/erk/commands/exec/discover_pr_for_issue.py` for canonical implementation:

```python
# Primary: Issue timeline lookup
pr_number = github.find_pr_by_issue(issue_number)

if pr_number is None:
    # Fallback: Git history investigation
    commits = git.search_commits(pattern=f"erk-plan #{issue_number}")
    if commits:
        branch = git.find_branch_for_commit(commits[0])
        pr_number = github.find_pr_by_branch(branch)
```

## Related Documentation

- [Session Management](../cli/session-management.md) - Session metadata structure
- [Plan Lifecycle](lifecycle.md) - Plan states and tracking
- [GitHub CLI Limits](../architecture/github-cli-limits.md) - API alternatives for large PRs
