# Plan: Prototype `!cd` Navigation for Claude Code Sessions

## Goal

Replace shell integration complexity with Claude Code's `!cd` command for worktree navigation. Instead of temp activation scripts + shell wrappers, commands output a path and Claude executes `!cd <path>`.

## Why This Will Work

1. **`!cd` is Claude Code internal** - Not a subprocess, so no Unix process model constraint
2. **Single session context** - Claude stays in same session, just changes working directory
3. **Simpler than shell integration** - No temp files, no sourcing, no wrapper functions

## Prototype: `plan-implement-on-new-worktree` Slash Command

Create a minimal end-to-end proof of concept:

1. Add `--claude-mode` flag to `wt checkout` command
2. Create slash command that calls it and uses `!cd`
3. Verify the workflow works

## Implementation Steps

### Step 1: Add `--claude-mode` Flag to `wt checkout`

**File**: `src/erk/cli/commands/wt/checkout_cmd.py`

Add a new `--claude-mode` flag (mutually exclusive with `--script`) that outputs just the path:

```python
@click.option(
    "--claude-mode",
    is_flag=True,
    hidden=True,
    help="Output path for Claude Code !cd navigation",
)
def wt_checkout(ctx: ErkContext, worktree_name: str, script: bool, claude_mode: bool) -> None:
    # ... existing validation ...

    if claude_mode:
        # Simple output: just the path
        user_output(str(worktree_path))
        return

    # ... existing script/subshell logic ...
```

### Step 2: Create `plan-implement-on-new-worktree` Slash Command

**File**: `.claude/commands/local/plan-implement-on-new-worktree.md`

```markdown
---
description: Create worktree and navigate to it (prototype)
argument-hint: "<worktree-name>"
---

# Plan-Implement on New Worktree (Prototype)

Test the !cd approach for worktree navigation.

## Instructions

1. Run: `erk wt checkout $ARGUMENTS --claude-mode`
2. Parse the output (it's just a path)
3. Execute: `!cd <path>`
4. Confirm navigation succeeded
```

### Step 3: Test the Workflow

1. Run `/local:plan-implement-on-new-worktree slot-01`
2. Verify Claude navigates to the worktree
3. Run `pwd` to confirm location

## Critical Files

- `src/erk/cli/commands/wt/checkout_cmd.py` - Add `--claude-mode` flag
- `.claude/commands/local/plan-implement-on-new-worktree.md` - New slash command

## What We're Testing

1. Can Claude parse erk command output and use `!cd`?
2. Does `!cd` work reliably for worktree paths?
3. Is this simpler than shell integration for Claude sessions?

## Future Extensions (if prototype works)

- Add `--claude-mode` to `implement` command
- Handle venv activation (may not be needed in Claude context)
- Eventually deprecate shell integration for Claude-first workflow

## Verification

After implementation:
1. Run `/local:plan-implement-on-new-worktree slot-01` (or any worktree name)
2. Confirm Claude is now in that worktree with `pwd`
3. Try navigating to "root" to return to main repo