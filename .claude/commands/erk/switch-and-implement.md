---
description: Switch to a different worktree and implement an issue
argument-hint: "<issue-number>"
---

# /erk:switch-and-implement

Switch to a different worktree and implement a GitHub issue. Requires shell wrapper integration.

## Prerequisites

- Shell wrapper must be active (`source <(erk shell-init)` in shell config)
- Issue must exist and have `erk-plan` label

## Agent Instructions

### Step 1: Write switch request markers

```bash
erk exec switch-request $ARGUMENTS --command /erk:plan-implement
```

### Step 2: Inform user

Output: "Switching to implementation worktree for issue #$ARGUMENTS..."

### Step 3: Terminate to trigger wrapper

```bash
kill -TERM $(ps -o ppid= -p $$)
```

The shell wrapper will:

1. Detect the switch-request marker
2. Run `erk implement <issue> --path-only` to set up worktree
3. cd to the new worktree
4. Activate venv if present
5. Restart Claude with `--continue /erk:plan-implement`

Claude resumes in the new worktree and `/erk:plan-implement` executes the implementation.
