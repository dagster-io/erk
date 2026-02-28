---
description: List open PRs in Claude Code terminal format
context: fork
agent: general-purpose
model: haiku
allowed-tools: Bash
---

# /erk:pr-list

List all open PRs in the current repository, formatted for Claude Code's terminal.

## Agent Instructions

### Step 1: Fetch Open PRs

Run:

```bash
gh pr list --state open --json number,title,headRefName,isDraft,reviewDecision,statusCheckRollup,createdAt,author,labels --limit 30
```

### Step 2: Display Results

Format output as a markdown table with these columns:

| #    | Title         | Branch     | Status | Checks | Created |
| ---- | ------------- | ---------- | ------ | ------ | ------- |
| #123 | Add feature X | feat/add-x | Draft  | 3/3    | 2d ago  |
| #456 | Fix login bug | fix/login  | Review | 2/5    | 1w ago  |

Column definitions:

- **#**: PR number prefixed with `#`
- **Title**: PR title, truncated to 40 characters if needed
- **Branch**: `headRefName`, truncated to 20 characters if needed
- **Status**: Derive from fields:
  - `isDraft: true` -> "Draft"
  - `reviewDecision: "APPROVED"` -> "Approved"
  - `reviewDecision: "CHANGES_REQUESTED"` -> "Changes"
  - Otherwise -> "Open"
- **Checks**: From `statusCheckRollup`, count passing vs total as "passing/total". If no checks, show "-"
- **Created**: Relative time (e.g., "2d ago", "1w ago")

If no open PRs found, report: "No open PRs found."

### Step 3: Suggest Next Steps

After listing, suggest:

- `gh pr view <number>` -- View PR details
- `gh pr checkout <number>` -- Check out the PR locally
