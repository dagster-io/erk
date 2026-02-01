---
title: Learn Without PR Context
read_when:
  - debugging learn workflow failures, implementing plans without creating PRs, understanding workflow variance in learn
---

# Learn Without PR Context

The standard learn workflow assumes a PR exists for the implemented plan, allowing it to fetch review comments via `gh pr diff` and PR comment analysis. However, valid workflow variance exists where plans are implemented without creating PRs first.

## Standard Learn Workflow Assumption

The async learn workflow expects:

1. Plan issue created
2. Implementation session occurs
3. **PR created** from implementation branch
4. Learn workflow fetches:
   - Session XML
   - `gh pr diff` output
   - PR review comments via GitHub API

**Source**: `src/erk/cli/commands/exec/scripts/fetch_learn_pr_comments.py`

## Workflow Variance: Implementation Without PR

**Valid scenario**: A plan is implemented but no PR is created because:

- Work is still in progress (not ready for review)
- Implementation was abandoned (decided not to proceed)
- Plan was consolidated with other work (different PR created)
- Local testing only (no intent to merge)

**Example**: Issue #6461 was implemented locally to test the learn workflow, but no PR was created initially.

## Graceful Degradation

When PR context is unavailable, learn workflow degrades gracefully:

### Step 1: PR Diff Fetch

```bash
gh pr diff --repo <owner>/<repo> <branch>
```

**When branch has no PR**:

- Command exits with error: "no pull requests found for branch X"
- Learn workflow catches error and continues
- No `pr-diff.txt` file generated

### Step 2: PR Comments Fetch

```bash
erk exec fetch-learn-pr-comments <issue_number> --output-dir <dir>
```

**When issue has no PR linkage**:

- Command outputs empty comments file: `pr-comments.json: []`
- Learn workflow processes empty comments (gracefully handles no feedback)

### Step 3: Documentation Generation

```bash
erk learn --async <issue_number>
```

**With empty PR context**:

- Learn agent generates documentation based solely on session XML
- No PR review feedback incorporated
- Plan description and session transcript still provide valuable context

## Detection Pattern

To check if PR exists for a branch:

```bash
gh pr view --repo <owner>/<repo> <branch> --json number
```

**Output**:

- Success: `{"number": 123}`
- No PR: Exit code 1, error message "no pull requests found"

## Implementation Guidance

When implementing learn-related commands that depend on PR context:

```python
# LBYL pattern for PR existence
pr_result = subprocess.run(
    ["gh", "pr", "view", branch, "--json", "number"],
    capture_output=True,
    text=True
)

if pr_result.returncode == 0:
    # PR exists, fetch comments and diff
    fetch_pr_comments(...)
    fetch_pr_diff(...)
else:
    # No PR, use graceful degradation
    write_empty_comments_file(...)
    skip_diff_generation()
```

**Anti-pattern**: Assuming PR always exists and crashing when it doesn't.

## Related Documentation

- [Async Learn Local Preprocessing](async-learn-local-preprocessing.md) — How learn materials are prepared
- [PR Comment Analysis](../pr-operations/pr-comment-analysis.md) — How review comments are processed
