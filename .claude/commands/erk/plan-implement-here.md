---
description: Fetch and implement a saved plan in the current pooled worktree
---

# /erk:plan-implement-here

Fetch a GitHub issue plan and implement it in the current worktree (assumes you're already in a pooled worktree slot).

## Usage

```
/erk:plan-implement-here <issue-number>
```

---

## Agent Instructions

### Step 1: Validate Argument

Extract the issue number from the argument (handles `#123` or `123` format).

If no issue number provided, display usage and stop:

```
Usage: /erk:plan-implement-here <issue-number>

Example: /erk:plan-implement-here 4015
```

### Step 2: Fetch and Execute

Run the pooled implement command:

```bash
erk pooled implement <issue-number>
```

This command:

1. Fetches the plan from the GitHub issue
2. Assigns the issue's branch to a pool slot
3. Creates `.impl/plan.md` in the worktree
4. Saves issue reference for PR linking
5. Launches into interactive implementation mode

### Step 3: Continue with Implementation

After the command completes setup, the `.impl/` folder will be created.
Invoke `/erk:plan-implement` to execute the implementation plan:

```
/erk:plan-implement
```

---

## Notes

- The issue must have the `erk-plan` label
- If the pool is full, you may need to run with `--force` to auto-unassign the oldest slot
- This differs from `erk implement` which creates a new worktree - this command uses existing pool slots
