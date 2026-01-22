---
description: Preview PR review feedback and planned actions
---

# /erk:pr-preview-address

## Description

Fetches unresolved PR review comments and discussion comments from the current branch's PR, then displays a summary showing what actions would be taken if `/erk:pr-address` were run. This is a preview-only command that makes no changes.

## Usage

```bash
/erk:pr-preview-address
/erk:pr-preview-address --all    # Include resolved threads
```

## Agent Instructions

> **IMPORTANT: This is a READ-ONLY preview command.**
>
> Do NOT make any code changes, resolve any threads, reply to any comments, or create any commits.

### Phase 1: Fetch Comments

Run both CLI commands to get all feedback:

```bash
erk exec get-pr-review-comments
erk exec get-pr-discussion-comments
```

If `--all` was specified, add `--include-resolved` to the first command:

```bash
erk exec get-pr-review-comments --include-resolved
```

### Phase 2: Handle No Comments Case

If both `threads` is empty AND `comments` is empty, display: "No unresolved review comments or discussion comments on PR #NNN."

### Phase 3: Classify & Summarize

For each comment, determine:

**Type:**

- **Review Thread**: Code-specific feedback from PR review
- **Discussion Comment**: General PR discussion

**Complexity and Proposed Action:**

> See `pr-operations` skill for the **Comment Classification Model**.

Determine proposed action for each:

- **Code change**: Requires modification to source files
- **Doc update**: Requires documentation changes
- **Already resolved**: Issue appears already addressed
- **Question to answer**: Needs a reply
- **No action**: Acknowledgment, no change needed
- **Investigate**: Requires codebase exploration

### Phase 4: Display Summary Table

Show a table with all feedback items:

```
## PR Feedback Summary

| # | Type | Location | Summary | Complexity | Proposed Action |
|---|------|----------|---------|------------|-----------------|
| 1 | Review | foo.py:42 | "Use LBYL pattern" | Local fix | Code change |
| 2 | Review | bar.py:15 | "Add type annotation" | Local fix | Code change |
| 3 | Review | impl.py (multiple) | "Rename variable" | Multi-location | Code change |
| 4 | Discussion | PR body | "Please update docs" | Cross-cutting | Doc update |
| 5 | Review | old.py:99 (outdated) | "Fix error handling" | Local fix | Already resolved |
```

### Phase 5: Display Batch Preview

Show how `/erk:pr-address` would group these items:

```
## Execution Plan Preview

If you run `/erk:pr-address`, comments would be processed in this order:

### Batch 1: Local Fixes (N comments)
| # | Location | Summary |
|---|----------|---------|
| 1 | foo.py:42 | Use LBYL pattern |
| 2 | bar.py:15 | Add type annotation |

### Batch 2: Single-File Changes (N comments)
| # | Location | Summary |
|---|----------|---------|
| 3 | impl.py (multiple) | Rename `old_name` to `new_name` throughout |

### Batch 3: Cross-Cutting Changes (N comments)
| # | Location | Summary |
|---|----------|---------|
| 4 | docs/ | Update documentation per reviewer request |

### Batch 4: Complex Changes (N comments -> 1 unified change)
| # | Location | Summary |
|---|----------|---------|
| 5 | impl.py + cmd.py | Related refactoring comments |
```

### Phase 6: Show Statistics

```
## Summary

- Total feedback items: N
- Review threads: N (N unresolved, N resolved)
- Discussion comments: N
- Estimated batches: N
- Auto-proceed batches (simple): N
- User confirmation batches (complex): N

To address these comments, run: /erk:pr-address
```

### Phase 7: Exit (NO ACTIONS)

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
