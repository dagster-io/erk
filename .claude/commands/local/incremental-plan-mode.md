---
description: Plan and implement a small change to the current PR
---

# /local:incremental-plan

Streamlines the "plan small change -> implement -> submit" loop for PR iteration.

## Usage

```bash
/local:incremental-plan
```

---

## Agent Instructions

### Step 1: Create Marker File

Before entering plan mode, create the incremental-plan marker to skip the "save as GitHub issue?" prompt later.

**Get the session ID** by reading the `session:` line from the system reminders in your conversation context (e.g., `session: a8e2cb1d-f658-4184-b359-b84bb67a487d`). This value is already visible in your context - just copy it directly, no tools needed.

```bash
erk exec marker create --session-id <session-id-from-reminder> incremental-plan
```

**IMPORTANT:** You must create this marker BEFORE calling EnterPlanMode.

### Step 2: Enter Plan Mode

Use the EnterPlanMode tool to begin planning.

### Step 3: Plan the Change

In plan mode:

1. **Ask the user** what change they want to make (if not already specified in the original prompt)
2. **Explore relevant code** using Glob, Grep, and Read tools
3. **Write a concise plan** to the plan file

#### Plan File Requirements

- **Fresh plan**: Overwrite the existing plan file completely. Do NOT combine with or reference any previous plan.
- **Focused scope**: This is for small, targeted changes - not major features.
- **Concise format**: Keep the plan brief and actionable.

### Step 4: Exit Plan Mode

When the plan is ready, call ExitPlanMode.

The incremental-plan marker you created in Step 1 will cause the exit-plan-mode-hook to:

- Skip the "save as GitHub issue?" prompt
- Proceed directly to implementation

### Step 5: Implement the Change

After exiting plan mode, implement the planned changes:

1. Load required skills (`dignified-python`, `fake-driven-testing` as needed)
2. Make the code changes
3. Write/update tests as appropriate
4. Report completion

### Step 6: Report Completion

When done, inform the user:

```
Implementation complete.

Next: Run /local:quick-submit to commit and push.
```

---

## Key Differences from Regular Plan Mode

| Aspect          | Regular Plan Mode         | Incremental Plan                |
| --------------- | ------------------------- | ------------------------------- |
| Plan file       | May combine with existing | Always overwritten (fresh)      |
| Save to GitHub? | Prompted                  | Skipped (implement immediately) |
| Scope           | Any size feature          | Small, focused changes          |
| Branch creation | May create worktree       | Stays in current worktree       |

---

## Error Cases

| Error           | Message                                                  |
| --------------- | -------------------------------------------------------- |
| No session ID   | Marker creation fails; normal plan mode behavior applies |
| Not in git repo | `Error: Not in a git repository`                         |

---

## Important Notes

- **DO NOT skip Step 1** - The marker must be created before entering plan mode
- **DO NOT save to GitHub** - This workflow skips issue creation
- **DO NOT create a new branch** - Changes go to the current branch
- The marker is automatically deleted when the exit-plan-mode-hook processes it
