---
title: "PR Operations: Duplicate Prevention and Detection"
read_when:
  - "creating PRs programmatically"
  - "implementing PR submission workflows"
  - "preventing duplicate PR creation"
tripwires:
  - action: "running gh pr create"
    warning: "Query for existing PRs first via `gh pr list --head <branch> --state all`. Prevents duplicate PR creation and workflow breaks."
---

# PR Operations: Duplicate Prevention and Detection

Critical patterns for preventing duplicate PR creation and detecting existing PRs.

## Table of Contents

- [Problem: Duplicate PRs](#problem-duplicate-prs)
- [Solution: Query Before Create](#solution-query-before-create)
- [Detection Patterns](#detection-patterns)
- [Automated Workflows](#automated-workflows)
- [Recovery from Duplicates](#recovery-from-duplicates)

---

## Problem: Duplicate PRs

### What Are Duplicate PRs?

Multiple PRs created for the same branch:

```
PR #1234: Feature X (branch: feature-x-01-15-1430)
PR #1235: Feature X (branch: feature-x-01-15-1430)  # Duplicate
```

### Why Duplicates Occur

1. **Retry Logic:** Command fails, user retries, creates second PR
2. **Race Conditions:** Concurrent workflow runs both create PRs
3. **Missing Detection:** Script doesn't check if PR already exists

### Problems Caused

- **Workflow confusion:** Which PR is the "real" one?
- **Review fragmentation:** Comments split across PRs
- **CI waste:** Both PRs trigger CI workflows
- **GitHub API errors:** Some operations fail with duplicates

---

## Solution: Query Before Create

### Pattern: Check, Then Create

Always check for existing PRs before creating a new one:

```bash
BRANCH_NAME="feature-x-01-15-1430"

# 1. Check for existing PR
EXISTING_PR=$(gh pr list --head "$BRANCH_NAME" --state all --json number -q '.[0].number')

if [ -n "$EXISTING_PR" ]; then
  echo "PR already exists: #$EXISTING_PR"
  gh pr view "$EXISTING_PR"
  exit 0
fi

# 2. Only create if none exists
gh pr create --title "Feature X" --body "..." --draft
```

### Why `--state all`?

The `--state all` flag includes:

- **Open PRs** (most common case)
- **Closed PRs** (intentionally closed, don't recreate)
- **Merged PRs** (already landed, definitely don't recreate)

Without `--state all`, you only check open PRs and might miss closed/merged ones.

### Why Query by Branch, Not Search?

```bash
# ✅ CORRECT: Query by branch (fast, precise)
gh pr list --head "$BRANCH_NAME" --state all

# ❌ WRONG: Search PR body (slow, unreliable)
gh pr list --search "Feature X in:title"
```

**Branch-based query advantages:**

- **Precise:** Exact match on branch name
- **Fast:** Indexed by GitHub
- **Reliable:** Branch names don't change

---

## Detection Patterns

### Pattern 1: Detect by Branch Name

```bash
# Get PR number for a specific branch
get_pr_for_branch() {
  local branch_name=$1
  gh pr list \
    --head "$branch_name" \
    --state all \
    --json number \
    -q '.[0].number'
}

BRANCH_NAME="P6172-add-context-pre-01-27-0820"
PR_NUMBER=$(get_pr_for_branch "$BRANCH_NAME")

if [ -n "$PR_NUMBER" ]; then
  echo "Found PR #$PR_NUMBER for branch $BRANCH_NAME"
fi
```

### Pattern 2: Detect by Issue Number

Use branch naming convention (erk branches start with `P{issue_number}-`):

```bash
# Get PR for an issue (by branch naming pattern)
get_pr_for_issue() {
  local issue_number=$1

  # Find branches matching P{issue}-*
  gh pr list \
    --search "head:P${issue_number}-" \
    --state all \
    --json number,headRefName \
    -q '.[0].number'
}

ISSUE_NUMBER=6172
PR_NUMBER=$(get_pr_for_issue "$ISSUE_NUMBER")
```

### Pattern 3: Check PR State

Determine if PR is open, closed, or merged:

```bash
get_pr_state() {
  local pr_number=$1
  gh pr view "$pr_number" --json state -q '.state'
}

PR_STATE=$(get_pr_state 1234)

case "$PR_STATE" in
  OPEN)
    echo "PR is open, can update"
    ;;
  CLOSED)
    echo "PR was closed (not merged), do not recreate"
    ;;
  MERGED)
    echo "PR was merged, do not recreate"
    ;;
esac
```

---

## Automated Workflows

### Reference: `/erk:git-pr-push`

The `/erk:git-pr-push` command handles duplicate prevention automatically:

**Location:** `.claude/commands/erk/git-pr-push.md`

**Pattern used:**

1. Check for existing PR by branch name
2. If PR exists:
   - Update PR body with new content
   - Skip creation
3. If no PR exists:
   - Create new draft PR
   - Set body with metadata

**Key snippet from command:**

```bash
# Check if PR already exists for this branch
EXISTING_PR=$(gh pr list --head "$CURRENT_BRANCH" --state all --json number -q '.[0].number')

if [ -n "$EXISTING_PR" ]; then
  echo "PR already exists: #$EXISTING_PR"
  echo "Updating PR body..."
  gh pr edit "$EXISTING_PR" --body "$PR_BODY"
else
  echo "Creating new PR..."
  gh pr create --title "$TITLE" --body "$PR_BODY" --draft
fi
```

### Workflow Best Practices

When implementing PR creation workflows:

1. **Always query first:** Never call `gh pr create` without checking
2. **Use `--state all`:** Don't miss closed/merged PRs
3. **Query by branch:** Most reliable detection method
4. **Handle all states:** Open, closed, merged have different meanings
5. **Update if exists:** Don't error, update the existing PR

---

## Recovery from Duplicates

### If Duplicates Already Exist

1. **Identify the "real" PR:**
   - Most recent PR
   - PR with most comments/reviews
   - PR referenced in issue comments
2. **Close duplicates:**
   ```bash
   gh pr close 1235 --comment "Duplicate of #1234"
   ```
3. **Update references:**
   - Update issue comments to point to correct PR
   - Update plan metadata if stored

### Preventing Future Duplicates

Add detection to all PR creation code paths:

```bash
# Template for safe PR creation
create_pr_safely() {
  local branch_name=$1
  local title=$2
  local body=$3

  # Check for existing PR
  local existing_pr=$(gh pr list --head "$branch_name" --state all --json number -q '.[0].number')

  if [ -n "$existing_pr" ]; then
    echo "PR already exists: #$existing_pr"
    return 0
  fi

  # Create new PR
  gh pr create --title "$title" --body "$body" --draft
}
```

---

## Command Reference

### Essential PR Detection Commands

#### List PRs for a Branch

```bash
gh pr list --head <branch-name> --state all
```

**Returns:** All PRs (open, closed, merged) for the branch

#### Get PR Number

```bash
gh pr list --head <branch-name> --state all --json number -q '.[0].number'
```

**Returns:** PR number as plain text (empty if none)

#### Check PR Exists

```bash
if gh pr view <branch-name> &>/dev/null; then
  echo "PR exists"
else
  echo "No PR found"
fi
```

**Note:** `gh pr view <branch>` works with branch names, not just PR numbers

#### Get PR State

```bash
gh pr view <number-or-branch> --json state -q '.state'
```

**Returns:** `OPEN`, `CLOSED`, or `MERGED`

#### Check PR is Open

```bash
STATE=$(gh pr view <number> --json state -q '.state')

if [ "$STATE" = "OPEN" ]; then
  echo "PR is open"
fi
```

---

## Review PR Creation Pattern

Plan review PRs follow a specialized creation pattern different from implementation PRs.

### Characteristics of Review PRs

- **Draft PRs**: Always created as drafts to prevent accidental merging
- **Ephemeral**: Never merged, closed after review completes
- **Labeled**: Tagged with `plan-review` label for filtering
- **Timestamped branches**: Named `plan-review-{issue}-{MM-DD-HHMM}`

### LBYL Pattern: Pre-Creation Validation

Review PR creation follows strict Look Before You Leap validation:

```python
# 1. Check issue exists
if not github_issues.issue_exists(repo_root, issue_number):
    raise CreateReviewPRException(error="issue_not_found", ...)

# 2. Check for duplicate PR by branch name
existing_pr = github.get_pr_for_branch(repo_root, branch_name)
if not isinstance(existing_pr, PRNotFound):
    raise CreateReviewPRException(error="pr_already_exists", ...)

# 3. Validate plan-header metadata exists
issue = github_issues.get_issue(repo_root, issue_number)
if find_metadata_block(issue.body, "plan-header") is None:
    raise CreateReviewPRException(error="invalid_issue", ...)

# 4. Only after all checks pass: create PR
pr_number = github.create_pr(...)
```

**Source**: `src/erk/cli/commands/exec/scripts/plan_create_review_pr.py` (lines 109-145)

### Duplicate Prevention via get_pr_for_branch()

The `get_pr_for_branch()` gateway method prevents duplicate review PRs:

```python
existing_pr = github.get_pr_for_branch(repo_root, branch_name)

# Discriminated union: Either PRNotFound or PR object
if not isinstance(existing_pr, PRNotFound):
    # PR already exists - error or update
    raise CreateReviewPRException(...)
```

This pattern:

- Returns discriminated union: `PR | PRNotFound`
- Checks **all PR states** (open, closed, merged)
- Uses branch name as exact match key

### BodyText Wrapper for GitHub API

Plan review creation uses `BodyText` wrapper for issue body updates:

```python
from erk_shared.gateway.github.types import BodyText

# Update issue body with review_pr field
updated_body = update_plan_header_review_pr(issue.body, pr_number)
github_issues.update_issue_body(
    repo_root,
    issue_number,
    BodyText(content=updated_body),  # Wrapper prevents raw string bugs
)
```

**Why BodyText**: Prevents accidentally passing unwrapped strings, enforces type safety at gateway boundary.

### plan-review Label Usage

Review PRs are tagged with `plan-review` label for identification:

```python
from erk.cli.constants import PLAN_REVIEW_LABEL

# Add label after PR creation
github.add_label_to_pr(repo_root, pr_number, PLAN_REVIEW_LABEL)
```

**Constant location**: `src/erk/cli/constants.py` (line 52)

**Label purpose**:

- Filter review PRs from implementation PRs in listings
- Trigger CI workflow exclusions (e.g., skip full CI for review PRs)
- Visual distinction in GitHub PR lists

### Why Draft PRs?

Review PRs are always created as drafts:

```python
pr_number = github.create_pr(
    repo_root,
    branch_name,
    pr_title,
    pr_body,
    base="master",
    draft=True,  # Always draft for review PRs
)
```

**Reasons**:

1. **Signal intent**: Clear visual indicator "not ready for merge"
2. **Prevent accidental merge**: GitHub prevents merging draft PRs
3. **Distinguish from implementation PRs**: Draft status helps identify purpose

---

## Integration with Erk Commands

### `erk exec get-pr-for-plan`

Uses this pattern internally:

```bash
erk exec get-pr-for-plan <issue_number>
```

**Implementation:**

1. Get `branch_name` from plan-header metadata
2. Query `gh pr list --head <branch_name> --state all`
3. Return PR number or sentinel value

**Sentinel values:**

- `no-branch-in-plan` - Plan not submitted (no branch created)
- Empty string - Branch exists but no PR found

### `erk plan submit`

Creates branch and PR, uses duplicate detection:

1. Check if branch already exists (reuse pattern)
2. Check if PR already exists for branch
3. Create PR only if none exists

---

## Related Documentation

- [Plan Lifecycle](../planning/lifecycle.md) - Phase 2 PR creation during plan submission
- [PR Submission Workflow](pr-submission.md) - Full git-only PR submission pattern
- [Git-PR-Push Command](../../../.claude/commands/erk/git-pr-push.md) - Reference implementation
