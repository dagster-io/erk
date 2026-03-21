# Make objective-update skill output predictable

## Context

When `erk land` runs `/erk:system:objective-update-with-landed-pr`, the output shows confusing `cat` commands reading from `~/.claude/projects/`:

```
> Running: cat /Users/schrockn/.claude/projects/-Users-schroc...
```

This is confusing because the user has no idea what these files are or why the agent is reading them. The root cause: the Claude agent executing the skill reads Claude Code's internal project context files on its own initiative. The output filter suppresses Read/Glob/Grep tools but shows all Bash commands, so `cat` via Bash leaks through.

The exec command already returns a comprehensive JSON blob with everything needed — the agent shouldn't need to forage for additional context.

## Changes

### 1. Add self-contained context directive to the skill

**File:** `.claude/commands/erk/system/objective-update-with-landed-pr.md`

Add a directive between Step 1 and Step 2:
- The JSON output from Step 1 contains ALL context needed for prose reconciliation
- Do NOT read additional files, use `cat`, or fetch extra context from `~/.claude/`
- All objective prose, PR details, and roadmap data are already in the JSON output

This addresses the root cause: telling the agent it has everything it needs.

### 2. Suppress `cat` on internal paths in output filter

**File:** `src/erk/core/output_filter.py`

In `summarize_tool_use` Bash handler (line 71-85), suppress `cat` commands targeting `~/.claude/` or `.claude/projects/` paths (return `None`, same as Read/Glob/Grep). This ensures that even if an agent still reads internal files, the user doesn't see confusing output.

## Verification

1. Run existing tests for `output_filter.py` to ensure suppression logic works
2. Manually verify on next `erk land` that no `cat` commands appear in output
