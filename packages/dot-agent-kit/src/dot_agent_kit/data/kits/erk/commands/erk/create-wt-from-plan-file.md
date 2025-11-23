---
description: Create worktree from existing plan file on disk
---

# /erk:create-wt-from-plan-file

Create an erk worktree from an existing plan file on disk.

## Usage

```bash
/erk:create-wt-from-plan-file
```

## What This Command Does

Delegates the complete worktree creation workflow to the `planned-wt-creator` agent, which handles:

1. Auto-detect most recent `*-plan.md` file at repository root
2. **Create GitHub issue from plan** (new step)
3. **Extract issue number from result** (new step)
4. **Create worktree via `erk create --from-issue <number>`** (changed from `--from-plan`)
5. Display next steps with issue link

**Note:** This workflow now ALWAYS creates a GitHub issue first. The issue becomes the single source of truth for the plan, enabling full traceability and integration with GitHub's PR workflow.

## Prerequisites

- At least one `*-plan.md` file at repository root
- Current working directory in a git repository
- Typically run after `/erk:save-context-enriched-plan`

## Implementation

When this command is invoked, delegate to the planned-wt-creator agent:

```
Task(
    subagent_type="planned-wt-creator",
    description="Create worktree from plan",
    prompt="Execute the complete planned worktree creation workflow"
)
```

The agent handles all workflow orchestration, error handling, and result reporting.
