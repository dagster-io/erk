# Plan: Add PR Analysis Pattern Documentation (Replan)

> **Replans:** #5680

## What Changed Since Original Plan

Investigation of the codebase reveals that **6 of the 7 original plan items are already implemented**:

| Original Item | Current Status |
|--------------|----------------|
| GitHub PR Operations subsection in erk-exec-commands.md | **IMPLEMENTED** (lines 31-35) |
| GitHub Issue Operations subsection in erk-exec-commands.md | **PARTIAL** - `get-issue-body`, `update-issue-body` documented in SKILL.md, but `close-issue-with-comment` only in reference.md |
| REST API Wrappers in github-api-rate-limits.md | **IMPLEMENTED** - comprehensive REST vs GraphQL guidance |
| Issue Operations in erk-exec/SKILL.md | **IMPLEMENTED** (lines 44-49) |
| **pr-analysis-pattern.md** | **NOT IMPLEMENTED** - file does not exist |
| Learn Workflow Pipeline Visualization | **IMPLEMENTED** (learn-workflow.md lines 346-367) |
| Scratch Storage Learn Conventions | **IMPLEMENTED** (scratch-storage.md + learn-workflow.md) |

The only truly missing documentation is `pr-analysis-pattern.md`.

## Investigation Findings

### Corrections to Original Plan

1. The original plan proposed adding many documentation items that already exist
2. Both `get-pr-commits` and `close-issue-with-comment` commands are fully implemented with comprehensive tests
3. The erk-exec skill's `reference.md` is auto-generated from code (`erk-dev gen-exec-reference-docs`), so manual updates would be overwritten

### Additional Details Discovered

1. **erk-exec-commands.md** already has a "PR Operations" section with `get-pr-review-comments`, `resolve-review-thread`, `reply-to-discussion-comment`
2. **github-api-rate-limits.md** already documents the REST vs GraphQL pattern comprehensively
3. **learn-workflow.md** has extensive pipeline documentation including "Stateless File-Based Composition" (lines 333-367)

## Remaining Gap

The only remaining documentation item is:

### pr-analysis-pattern.md

A new documentation file that provides narrative guidance for using PR analysis commands together in workflows. This would document the metadata-first approach (files → commits → diff) and show how commands like `get-pr-commits` fit into larger workflows.

## Implementation Steps

### Step 1: Create pr-analysis-pattern.md

**Location:** `docs/learned/planning/pr-analysis-pattern.md`
**Action:** CREATE

Create the file with:

```markdown
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

| Command | Purpose |
|---------|---------|
| `erk exec get-pr-commits` | Fetch PR commits (REST API) |
| `erk exec get-pr-review-comments` | Fetch review threads |
| `erk exec get-issue-body` | Fetch issue body (REST API) |
| `gh pr view --json files` | Get changed files inventory |
```

### Step 2: Update docs/learned/index.md

Add entry for the new document under the planning section.

## Files to Modify

1. `docs/learned/planning/pr-analysis-pattern.md` (CREATE)
2. `docs/learned/index.md` (UPDATE - add entry)

## Verification

1. Run `make format` to ensure proper formatting
2. Verify the new file renders correctly with frontmatter
3. Confirm index.md links to the new document