---
title: PR Operations: Duplicate Prevention and Detection
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
