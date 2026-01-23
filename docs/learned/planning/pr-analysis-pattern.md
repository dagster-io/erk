---
title: PR Analysis Pattern
read_when:
  - "analyzing PR changes for documentation"
  - "building workflows that inspect PRs"
---

# PR Analysis Pattern

When analyzing PR changes for semantic understanding, use a metadata-first approach.

## Step 1: File-Level Inventory

```bash
gh pr view <PR> --json files,additions,deletions
```

This gives you:

- List of changed files with paths
- Addition/deletion counts for scope estimation
- Quick categorization (new files vs modified)

## Step 2: Commit-Level Detail

```bash
erk exec get-pr-commits <PR>
```

This gives you:

- Individual commit SHAs
- Commit messages explaining intent
- Chronological ordering of changes

**Why use erk exec?** Uses REST API (avoids GraphQL rate limits), tested with FakeGitHub, consistent JSON output format.

## Step 3: Semantic Analysis

For deeper understanding, read diffs or use diff analysis agents that can:

- Identify new functions/classes added
- Detect pattern changes
- Find documentation opportunities

## Example: Learn Workflow

The `/erk:learn` workflow uses this pattern:

1. `gh pr view --json files` for file inventory
2. `erk exec get-pr-commits` for commit history
3. CodeDiffAnalyzer agent for semantic understanding

This combination provides a complete picture of what was built, why, and how.

## Related Commands

| Command                           | Purpose                     |
| --------------------------------- | --------------------------- |
| `erk exec get-pr-commits`         | Fetch PR commits (REST API) |
| `erk exec get-pr-review-comments` | Fetch review threads        |
| `erk exec get-issue-body`         | Fetch issue body (REST API) |
| `gh pr view --json files`         | Get changed files inventory |
