---
description: Preview PR review feedback and planned actions
---

# /erk:pr-preview-address

## Description

Fetches unresolved PR review comments and discussion comments, displays a summary of what `/erk:pr-address` would do. This is a read-only preview command that makes no changes.

## Usage

```bash
/erk:pr-preview-address
/erk:pr-preview-address --all    # Include resolved threads
```

## Agent Instructions

> **IMPORTANT: This is a READ-ONLY preview command.**
>
> Do NOT make any code changes, resolve any threads, reply to any comments, or create any commits.

### Phase 1: Classify Feedback

Invoke the pr-feedback-classifier skill to fetch and classify all PR feedback:

```
/pr-feedback-classifier [--include-resolved if --all was specified]
```

Parse the JSON response.

### Phase 2: Display Results

**Handle errors**: If `success` is false, display the error and exit.

**Handle no comments**: If both `actionable_threads` and `discussion_actions` are empty, display: "No unresolved review comments or discussion comments on PR #NNN." and exit.

**Format the results** as a human-readable summary:

```
## PR #5944: "Feature: Add new API endpoint"

### Actionable Items (N total)

| # | Type | Location | Summary | Complexity |
|---|------|----------|---------|------------|
| 1 | review | foo.py:42 | Use LBYL pattern | local |
| 2 | review | bar.py:15 | Add type annotation | local |
| 3 | discussion | - | Update documentation | cross_cutting |

### Execution Plan Preview

**Batch 1: Local Fixes** (auto-proceed)
- Item #1: foo.py:42 - Use LBYL pattern
- Item #2: bar.py:15 - Add type annotation

**Batch 2: Cross-Cutting** (user confirmation)
- Item #3: Update documentation

### Statistics
- Actionable items: 3
- Informational skipped: 12
- Estimated batches: 2
- Auto-proceed batches: 1
- User confirmation batches: 1
```

Add footer:

```
To address these comments, run: /erk:pr-address
```

### Phase 3: Exit (NO ACTIONS)

**CRITICAL**: This is a preview-only command. Do NOT:

- Make any code changes
- Resolve any threads
- Reply to any comments
- Create any commits
- Push anything to remote
- Run any CI commands

Simply display the summary and exit.

## Error Handling

**No PR for branch:** Display error and suggest creating a PR with `gt create` or `gh pr create`

**GitHub API error:** Display error and suggest checking `gh auth status` and repository access
