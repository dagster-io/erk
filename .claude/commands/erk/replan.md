---
description: Replan an existing erk-plan issue against current codebase state
argument-hint: <issue-number-or-url>
---

# /erk:replan

Recomputes existing erk-plan issue(s) against the current codebase state, creating a new plan and closing the original(s).

Supports consolidating multiple plans into a single unified plan.

## Usage

```bash
/erk:replan 2521                          # Single plan replan
/erk:replan https://github.com/owner/repo/issues/2521
/erk:replan 123 456 789                   # Consolidate multiple plans
```

---

## Agent Instructions

### Step 1: Parse Issue References

Split `$ARGUMENTS` on whitespace. For each argument:

- If numeric (e.g., `2521`), use directly as issue number
- If URL (e.g., `https://github.com/owner/repo/issues/2521`), extract the number from the path

Store all issue numbers in a list. Set `CONSOLIDATION_MODE=true` if multiple issues provided.

If no argument provided, ask the user for the issue number.

### Step 2: Validate All Plans (Parallel if Multiple)

For each issue number, fetch and validate:

```bash
erk exec get-issue-body <number>
```

This returns JSON with `{success, issue_number, title, body, state, labels, url}`. Store each issue's title.

Validate each issue:

1. Issue exists
2. Issue has `erk-plan` label

If any issue is not an erk-plan issue, display error and abort:

```
Error: Issue #<number> is not an erk-plan issue (missing erk-plan label).
```

If any issue is already closed, display warning but continue:

```
Warning: Issue #<number> is already closed. Proceeding with replan anyway.
```

### Step 3: Fetch Plan Content (Parallel if Multiple)

For each issue, fetch the plan content stored in the first comment's `plan-body` metadata block:

```bash
gh issue view <number> --comments --json comments
```

Parse the first comment to find `<!-- erk:metadata-block:plan-body -->` section.

Extract the plan content from within the `<details>` block.

If no plan-body found for any issue, display error:

```
Error: No plan content found in issue #<number>. Expected plan-body metadata block in first comment.
```

### Step 4: Deep Investigation

Use the Explore agent (Task tool with subagent_type=Explore) to perform deep investigation of the codebase.

**If CONSOLIDATION_MODE:**

Launch parallel Explore agents (one per plan, using `run_in_background: true`), each investigating:

- Plan items and their current status
- Overlap potential with other plans being consolidated
- File mentions and their current state

**For each plan (parallel or sequential):**

#### 4a: Check Plan Items Against Codebase

For each implementation item in the plan:

- Search for relevant files, functions, or patterns
- Determine status: **implemented**, **partially implemented**, **not implemented**, or **obsolete**

Build a comparison table showing:

| Plan Item | Current Status | Notes |
| --------- | -------------- | ----- |
| ...       | ...            | ...   |

#### 4b: Deep Investigation (MANDATORY)

Go beyond the plan items to understand the actual implementation:

1. **Data Structures**: Find all relevant types, dataclasses, and their fields
2. **Helper Functions**: Identify utility functions and their purposes
3. **Lifecycle & State**: Understand how state flows through the system
4. **Naming Conventions**: Document actual names used (not guessed names)
5. **Entry Points**: Map all places that trigger the relevant functionality
6. **Configuration**: Find config options, defaults, and overrides

#### 4c: Document Corrections and Discoveries

Create two lists per plan:

1. **Corrections to Original Plan**: Wrong assumptions, incorrect names, outdated information
2. **Additional Details**: Implementation specifics, architectural insights, edge cases

### Step 4d: Consolidation Analysis (CONSOLIDATION_MODE only)

If consolidating multiple plans:

1. **Identify Overlap**: Find items that appear in multiple plans
2. **Merge Strategy**: Determine how to combine overlapping items
3. **Dependency Ordering**: Order items by dependency across all plans
4. **Attribution Tracking**: Track which items came from which plan

### Step 5: Post Investigation to Original Issue(s)

Before creating the new plan, post investigation findings to each original issue as a comment:

```bash
gh issue comment <original_number> --body "## Deep Investigation Notes (for implementing agent)

### Corrections to Original Plan
- [List corrections discovered]

### Additional Details Not in Original Plan
- [List new details discovered]

### Key Architectural Insights
- [List important discoveries]"
```

If consolidating, include note:

```
Note: This plan is being consolidated with #<other_numbers> into a unified plan.
```

### Step 6: Create New Plan (Always)

**Always create a new plan issue**, regardless of implementation status.

Use EnterPlanMode to create an updated plan.

---

#### Single Plan Format

```markdown
# Plan: [Updated Title]

> **Replans:** #<original_issue_number>

## What Changed Since Original Plan

- [List major codebase changes that affect this plan]

## Investigation Findings

### Corrections to Original Plan

- [List any wrong assumptions or incorrect names]

### Additional Details Discovered

- [List implementation specifics not in original plan]

## Remaining Gaps

- [List items from original plan that still need implementation]

## Implementation Steps

1. [Updated step 1]
2. [Updated step 2]
```

---

#### Consolidated Plan Format (CONSOLIDATION_MODE)

```markdown
# Plan: [Unified Title]

> **Consolidates:** #123, #456, #789

## Source Plans

| #   | Title              | Items Merged |
| --- | ------------------ | ------------ |
| 123 | [Title from issue] | X items      |
| 456 | [Title from issue] | Y items      |
| 789 | [Title from issue] | Z items      |

## What Changed Since Original Plans

- [List major codebase changes affecting any of the plans]

## Investigation Findings

### Corrections to Original Plans

- **#123**: [corrections]
- **#456**: [corrections]
- **#789**: [corrections]

### Additional Details Discovered

- [Combined implementation specifics]

### Overlap Analysis

- [Items that appeared in multiple plans, now merged]

## Remaining Gaps

- [Combined items that still need implementation]

## Implementation Steps

1. [Step] _(from #123)_
2. [Merged step] _(from #123, #456)_
3. [Step] _(from #456)_
4. [Step] _(from #789)_

## Attribution

Items by source:

- **#123**: Steps 1, 2
- **#456**: Steps 2, 3
- **#789**: Step 4
```

---

### Step 7: Save and Close

After the user approves the plan in Plan Mode:

1. Exit Plan Mode
2. Run `/erk:plan-save` to create the new GitHub issue
3. Close original issue(s) with comment linking to the new one:

**Single plan:**

```bash
gh issue close <original_number> --comment "Superseded by #<new_number> - see updated plan that accounts for codebase changes."
```

**Consolidated plans:**

```bash
gh issue close 123 --comment "Consolidated into #<new_number> with #456, #789"
gh issue close 456 --comment "Consolidated into #<new_number> with #123, #789"
gh issue close 789 --comment "Consolidated into #<new_number> with #123, #456"
```

Display final summary:

**Single plan:**

```
✓ Created new plan issue #<new_number>
✓ Closed original issue #<original_number>

Next steps:
- Review the new plan: gh issue view <new_number>
- Submit for implementation: erk plan submit <new_number>
```

**Consolidated plans:**

```
✓ Created consolidated plan issue #<new_number>
✓ Closed original issues: #123, #456, #789

Source plans consolidated:
- #123: [title]
- #456: [title]
- #789: [title]

Next steps:
- Review the consolidated plan: gh issue view <new_number>
- Submit for implementation: erk plan submit <new_number>
```

---

## Error Cases

| Error                    | Message                                                                       |
| ------------------------ | ----------------------------------------------------------------------------- |
| Issue not found          | `Error: Issue #<number> not found.`                                           |
| Not an erk-plan          | `Error: Issue #<number> is not an erk-plan issue (missing erk-plan label).`   |
| No plan content          | `Error: No plan content found in issue #<number>.`                            |
| GitHub CLI not available | `Error: GitHub CLI (gh) not available. Run: brew install gh && gh auth login` |
| No network               | `Error: Unable to reach GitHub. Check network connectivity.`                  |

---

## Important Notes

- **DO NOT implement the plan** - This command only creates an updated plan
- **DO NOT skip codebase analysis** - Always verify current state before replanning
- **Use Explore agent** for comprehensive codebase searches (Task tool with subagent_type=Explore)
- **Parallel investigation** for multiple plans (run_in_background: true)
- Original issue(s) closed only after the new plan is successfully created
- The new plan references all original issue(s) for traceability
