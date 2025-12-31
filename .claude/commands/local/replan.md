---
description: Replan an existing erk-plan issue against current codebase state
argument-hint: <issue-number-or-url>
---

# /erk:replan

Recomputes an existing erk-plan issue against the current codebase state, creating a new plan and closing the original.

## Usage

```bash
/erk:replan 2521
/erk:replan https://github.com/owner/repo/issues/2521
```

---

## Agent Instructions

### Step 1: Parse Issue Reference

Extract the issue number from the argument:

- If numeric (e.g., `2521`), use directly
- If URL (e.g., `https://github.com/owner/repo/issues/2521`), extract the number from the path

If no argument provided, ask the user for the issue number.

### Step 2: Fetch Original Issue

```bash
gh issue view <number> --json title,body,state,labels
```

Store the issue title and check that:

1. Issue exists
2. Issue has `erk-plan` label

If not an erk-plan issue, display error:

```
Error: Issue #<number> is not an erk-plan issue (missing erk-plan label).
```

If issue is already closed, display warning but continue:

```
Warning: Issue #<number> is already closed. Proceeding with replan anyway.
```

### Step 3: Fetch Plan Content

The plan content is stored in the first comment's `plan-body` metadata block:

```bash
gh issue view <number> --comments --json comments
```

Parse the first comment to find `<!-- erk:metadata-block:plan-body -->` section.

Extract the plan content from within the `<details>` block.

If no plan-body found, display error:

```
Error: No plan content found in issue #<number>. Expected plan-body metadata block in first comment.
```

### Step 4: Analyze Codebase

Use the Explore agent (Task tool with subagent_type=Explore) to check the current codebase state against each item in the original plan.

For each implementation item in the plan:

- Search for relevant files, functions, or patterns
- Determine status: **implemented**, **partially implemented**, **not implemented**, or **obsolete**

Build a comparison table showing:

| Plan Item | Current Status | Notes |
| --------- | -------------- | ----- |
| ...       | ...            | ...   |

### Step 5: Create Assessment

Based on the analysis, determine the overall status:

1. **Fully implemented**: All items are complete
   - Display: "Plan #<number> appears to be fully implemented. No replan needed."
   - Ask user if they want to close the issue

2. **Fully obsolete**: The approach is no longer valid (e.g., feature removed, architecture changed)
   - Display: "Plan #<number> is obsolete due to [reasons]."
   - Suggest closing the original issue

3. **Partial work remains**: Some items implemented, others pending
   - Continue to Step 6

### Step 6: Enter Plan Mode

If partial work remains, use EnterPlanMode to create an updated plan.

The new plan should include:

#### Header Section

```markdown
# Plan: [Updated Title]

> **Replans:** #<original_issue_number>
```

#### What Changed Section

```markdown
## What Changed Since Original Plan

- [List major codebase changes that affect this plan]
- [Reference specific PRs or commits if relevant]
```

#### Remaining Gaps Section

```markdown
## Remaining Gaps

- [List items from original plan that still need implementation]
- [Note any items that are partially done]
```

#### Implementation Steps Section

```markdown
## Implementation Steps

1. [Updated step 1]
2. [Updated step 2]
   ...
```

### Step 7: Save and Close

After the user approves the plan in Plan Mode:

1. Exit Plan Mode
2. Run `/erk:plan-save` to create the new GitHub issue
3. Close the original issue with a comment linking to the new one:

```bash
gh issue close <original_number> --comment "Superseded by #<new_number> - see updated plan that accounts for codebase changes."
```

Display final summary:

```
✓ Created new plan issue #<new_number>
✓ Closed original issue #<original_number>

Next steps:
- Review the new plan: gh issue view <new_number>
- Submit for implementation: erk plan submit <new_number>
```

---

## Error Cases

| Error                    | Message                                                                       |
| ------------------------ | ----------------------------------------------------------------------------- |
| Issue not found          | `Error: Issue #<number> not found.`                                           |
| Not an erk-plan          | `Error: Issue #<number> is not an erk-plan issue (missing erk-plan label).`   |
| No plan content          | `Error: No plan content found in issue #<number>.`                            |
| Plan fully implemented   | `Plan #<number> appears to be fully implemented. No replan needed.`           |
| Plan fully obsolete      | `Plan #<number> is obsolete. Consider closing it.`                            |
| GitHub CLI not available | `Error: GitHub CLI (gh) not available. Run: brew install gh && gh auth login` |
| No network               | `Error: Unable to reach GitHub. Check network connectivity.`                  |

---

## Important Notes

- **DO NOT implement the plan** - This command only creates an updated plan
- **DO NOT skip codebase analysis** - Always verify current state before replanning
- **Use Explore agent** for comprehensive codebase searches (Task tool with subagent_type=Explore)
- The original issue is closed only after the new plan is successfully created
- The new plan references the original issue for traceability
