# Plan: Create `/local:cmux-workspace-rename` command

## Context

When working in CMUX workspaces, the workspace name often doesn't match the current git branch. This command provides a quick way to rename the current CMUX workspace to match the current branch name.

## Implementation

Create a single file: `.claude/commands/local/cmux-workspace-rename.md`

The command will:
1. Get the current branch via `git branch --show-current`
2. Run `cmux rename-workspace "<branch>"` (omitting `--workspace` targets the current workspace via `$CMUX_WORKSPACE_ID`)
3. Confirm the rename to the user

Structure follows the minimal command pattern — no frontmatter complexity needed since this is a simple two-step bash operation.

## File to create

**`.claude/commands/local/cmux-workspace-rename.md`**

```markdown
---
description: Rename current CMUX workspace to the current git branch name
allowed-tools: Bash
---

Run the following two commands sequentially:

1. Get the current git branch name:
   ```bash
   git branch --show-current
   ```

2. Rename the current CMUX workspace to that branch name:
   ```bash
   cmux rename-workspace "<branch>"
   ```

Tell the user the workspace was renamed to the branch name.
```

## Verification

- Run `/local:workspace-rename` in a CMUX workspace on a feature branch
- Confirm the workspace tab/label updates to the branch name
