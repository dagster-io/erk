---
description: Implement plan in current session - saves to GitHub, creates worktree, runs implementation
---

# /erk:implement-in-session

Implements a plan within the current Claude Code session by:

1. Saving the plan to GitHub as an issue (or using an existing issue)
2. Creating a new worktree with P-naming pattern
3. Changing directory to the worktree
4. Running post-create hooks (venv activation)
5. Delegating implementation to `/erk:system:impl-execute`

## Prerequisites

- Must be in a git repository managed by erk
- Either: a plan in `~/.claude/plans/` (from plan mode), OR an existing erk-plan issue number
- GitHub CLI (`gh`) must be authenticated

## When to Use This Command

Use this command when you want to implement a plan in a **new worktree** within the same session.

**Key difference from `/erk:system:impl-execute`**: This command creates a new worktree, while `impl-execute` implements in the current worktree.

---

## Agent Instructions

### Step 1: Determine Issue Number

Check if the user provided an issue number as an argument:

- **If issue number provided**: Use it directly, skip to Step 3
- **If no issue number**: Proceed to Step 2 to save the plan

### Step 2: Save Plan to GitHub (if needed)

Extract the session ID from the `session:` line in the `SESSION_CONTEXT` reminder.

Save the current plan to GitHub:

```bash
erk exec plan-save-to-issue --format json --session-id="<session-id>"
```

Parse the JSON output to get the `issue_number`.

If this fails, display the error and stop.

### Step 3: Create Worktree from Plan

Create a new worktree using the issue:

```bash
erk wt create --from-plan <issue_number> --json --stay
```

This command:

- Creates worktree with P-naming pattern (e.g., `P123-fix-auth-bug-01-15-1430`)
- Creates `.impl/` folder with `plan.md` and `issue.json`
- Runs post-create hooks from `.erk/config.toml` (e.g., `uv sync`)
- Returns JSON with `worktree_path`

The `--stay` flag prevents automatic shell navigation since we'll `cd` manually.

Parse the JSON output to get the `worktree_path`.

If this fails, display the error and stop.

### Step 4: Change Directory to Worktree

Use Bash to change to the new worktree:

```bash
cd <worktree_path>
```

Then verify the change succeeded:

```bash
pwd
```

### Step 5: Delegate to impl-execute

Now that the worktree is set up with `.impl/`, delegate all remaining work to `/erk:system:impl-execute`.

Load and execute the `/erk:system:impl-execute` command, which handles:

- Reading plan and loading context
- Creating TodoWrite entries
- Signaling GitHub events
- Executing plan phases
- Running CI
- Submitting PR

---

## Command Flow Diagram

```
Session with plan OR existing issue number
    │
    ├── [If no issue number provided]
    │   ▼
    │   erk exec plan-save-to-issue --session-id="..." --format json
    │   │ Returns: {"issue_number": 123, ...}
    │   ▼
    ▼
erk wt create --from-plan <issue_number> --json --stay
    │ Creates: P123-fix-auth-bug-01-15-1430/
    │ Sets up: .impl/plan.md, .impl/issue.json
    │ Runs: post-create hooks (uv sync, etc.)
    │ Returns: {"worktree_path": "/path/to/worktree", ...}
    ▼
cd /path/to/worktree
    │
    ▼
/erk:system:impl-execute
    │ (handles all implementation steps)
    ▼
Done
```

---

## Related Commands

- `/erk:system:impl-execute` - Implement in current worktree (no new worktree)
- `/erk:plan-save` - Save plan only, don't implement (for defer-to-later workflow)
- `/erk:plan-implement-here` - Implement from existing GitHub issue (skips save step)
