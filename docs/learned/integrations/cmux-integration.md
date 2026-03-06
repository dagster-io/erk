---
title: CMUX Integration
read_when:
  - "working with cmux workspace management"
  - "understanding erk's cmux integration points"
tripwires: []
---

# CMUX Integration

Erk integrates with [cmux](https://github.com/dagster-io/cmux), a terminal multiplexer, for workspace management.

## Workspace Rename Command

`/local:cmux-workspace-rename` is a slash command that renames the current cmux workspace to match the current git branch name. It runs two sequential commands:

1. `git branch --show-current` — get the current branch name
2. `cmux rename-workspace "<branch>"` — rename the workspace

**Source:** `.claude/commands/local/cmux-workspace-rename.md`

## TUI Integration

The TUI provides a `cmux_checkout` command (launch key `m`) that creates a cmux workspace, checks out the PR, and syncs with trunk. This is integrated into the TUI workflow rather than being a standalone CLI command.

### When to Use Each

| Tool                           | Context         | Use When                                  |
| ------------------------------ | --------------- | ----------------------------------------- |
| `/local:cmux-workspace-rename` | Claude Code CLI | Standalone rename during a Claude session |
| TUI `cmux_checkout` (key `m`)  | Erk TUI         | Checkout PR while using the TUI           |
