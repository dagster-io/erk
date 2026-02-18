# Slash Command Reference

Claude Code slash commands for in-session use.

<!-- TODO: This document is a skeleton. Fill in the sections below. -->

## Overview

<!-- TODO: What slash commands are and how to use them -->

## Implementation Commands

<!-- TODO: /erk:plan-implement, /erk:plan-save, /erk:plan-implement-here -->

## PR Commands

<!-- TODO: /erk:pr-submit, /erk:pr-address -->

## Iteration Commands

<!-- TODO: /quick-submit, /erk:auto-restack, /erk:fix-conflicts -->

## Navigation Commands

### /erk:land

Merge a PR and clean up worktree. Optionally updates linked objectives.

### /erk:objective-inspect

View an objective's dependency graph, progress, and associated plans/PRs. Read-only command that works in plan mode.

```bash
/erk:objective-inspect 3679
/erk:objective-inspect  # auto-detects from current branch
```

### /erk:objective-plan

Create an implementation plan from a specific objective roadmap step.

## Documentation Commands

<!-- TODO: /erk:learn -->

## Local Commands

<!-- TODO: /local:* commands -->

## See Also

- [CLI Command Reference](commands.md) - CLI commands
- [The Workflow](../topics/the-workflow.md) - When to use each command
