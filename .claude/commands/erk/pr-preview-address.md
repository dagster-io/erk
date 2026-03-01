---
description: Preview PR review feedback and planned actions
---

# /erk:pr-preview-address

## Description

Fetches unresolved PR review comments and discussion comments, displays a summary of what `/erk:pr-address` would do. This is a read-only preview command that makes no changes.

## Usage

```bash
/erk:pr-preview-address
/erk:pr-preview-address --all               # Include resolved threads
/erk:pr-preview-address --pr 6631           # Target specific PR
/erk:pr-preview-address --pr 6631 --all     # Target specific PR with resolved threads
```

## Agent Instructions

> **IMPORTANT: This is a READ-ONLY preview command.**
>
> Do NOT make any code changes, resolve any threads, reply to any comments, or create any commits.

### Phase 1: Classify Feedback

Invoke the pr-feedback-classifier skill to fetch and classify all PR feedback:

```
/pr-feedback-classifier [--pr <number> if specified] [--include-resolved if --all was specified]
```

Parse the JSON response.

### Phase 2: Display Results

**Handle errors**: If `success` is false, display the error and exit.

**Handle no comments**: If `actionable_threads` is empty and `discussion_actions` is empty, display: "No unresolved review comments or discussion comments on PR #NNN." and exit.

**Format the results** as a human-readable summary:

```
## PR #5944: "Feature: Add new API endpoint"

### Pre-Existing Items (Auto-Resolve) (N total)

| # | Type | Location | Summary |
|---|------|----------|---------|
| 1 | review | old_module.py:30 | Bot: use LBYL pattern (pre-existing in moved code) |
| 2 | review | old_module.py:55 | Bot: add type annotation (pre-existing in moved code) |

### Actionable Items (N total)

| # | Type | Location | Classification | Summary | Complexity |
|---|------|----------|----------------|---------|------------|
| 1 | review | foo.py:42 | actionable | Use LBYL pattern | local |
| 2 | review | bar.py:15 | actionable | Add type annotation | local |
| 3 | discussion | - | actionable | Update documentation | cross_cutting |

### Informational Items (N total)

| # | Type | Location | Summary | Complexity |
|---|------|----------|---------|------------|
| 4 | review | utils.py:10 | Bot suggestion: extract helper (optional) | local |

### Execution Plan Preview

**Batch 0: Pre-Existing (Auto-Resolve)** (auto-proceed, no code changes)
- Item #1: old_module.py:30 - Bot: use LBYL pattern (pre-existing)
- Item #2: old_module.py:55 - Bot: add type annotation (pre-existing)

**Batch 1: Local Fixes** (auto-proceed)
- Item #3: foo.py:42 - Use LBYL pattern
- Item #4: bar.py:15 - Add type annotation

**Batch 2: Cross-Cutting** (user confirmation)
- Item #5: Update documentation

**Batch 3: Informational** (user decides: act or dismiss)
- Item #6: utils.py:10 - Bot suggestion: extract helper (optional)

### Statistics
- Pre-existing items (auto-resolve): 2
- Actionable items: 3
- Informational items: 1
- Informational discussion comments: 12
- Estimated batches: 4
- Auto-proceed batches: 2
- User confirmation batches: 2
```

**Note:** Items in `actionable_threads` are split into three sections based on their `pre_existing` and `classification` fields: `pre_existing: true` items appear under "Pre-Existing Items (Auto-Resolve)", `"actionable"` items appear under "Actionable Items", `"informational"` items appear under "Informational Items". All sections use continuous item numbering.

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
