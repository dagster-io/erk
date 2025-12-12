# Plan: Update conflict message wording

## Summary
Change "Falling back to Claude..." to "Intelligently resolving merge conflicts with Claude" in the auto-restack command output.

## Files to modify

1. **`src/erk/cli/commands/pr/auto_restack_cmd.py:82`** - Change the message string
2. **`docs/agent/erk/auto-restack.md:154`** - Update the documentation example to match

## Change details

Replace:
```
Conflicts detected in {n} file(s). Falling back to Claude...
```

With:
```
Conflicts detected in {n} file(s). Intelligently resolving merge conflicts with Claude
```