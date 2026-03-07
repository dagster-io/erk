---
name: cmux
description: This skill should be used when working with cmux, the terminal multiplexer application. Use when users mention cmux commands, workspace management, terminal pane operations, or cmux integration with erk. Essential for understanding cmux's workspace model, CLI commands, and scripting patterns.
---

# cmux - Terminal Multiplexer

## Overview

**cmux** is a native macOS terminal application (Swift/AppKit) that provides terminal multiplexing with workspaces, panes, and splits. It uses Ghostty's rendering engine (libghostty) for GPU-accelerated terminal output. The CLI communicates with the running app via a Unix domain socket at `/tmp/cmux.sock`.

Think of cmux as "tmux reimagined as a native macOS app" -- it has workspaces (like tmux windows), panes (like tmux panes), and surfaces (individual terminal or browser instances within panes), all controllable via a rich CLI.

## When to Load the Reference

This skill covers the mental model, common commands, gotchas, and erk integration. Load `references/cmux-reference.md` when you need:

- **Browser automation** syntax (40+ subcommands: navigation, forms, cookies, storage, console, waiting, dialogs, downloads, state)
- **Window management** (`list-windows`, `new-window`, `focus-window`, `close-window`, `move-workspace-to-window`)
- **Surface management** (`move-surface`, `reorder-surface`, `drag-surface-to-split`, `surface-health`)
- **Panel/Tab** commands (`list-panels`, `focus-panel`, `tab-action`, `rename-tab`)
- **Sidebar metadata** (`clear-status`, `list-status`, `clear-progress`, `clear-log`, `list-log`, `sidebar-state`)
- **Full tmux compat** (20+ commands: `pipe-pane`, `wait-for`, `copy-mode`, `set-hook`, `bind-key`, `popup`, etc.)
- **Utility/diagnostic** (`ping`, `capabilities`, `claude-hook`, `set-app-focus`)
- **Workflow recipes** (browser automation, layout scripting, notification workflows)

## Core Concepts

### Object Hierarchy

```
Window (top-level OS window)
  +-- Workspace (vertical tab, like a tmux window)
        +-- Pane (a split region)
              +-- Surface (terminal or browser instance)
```

- **Window**: macOS application window. Multiple windows supported.
- **Workspace**: A tab in the sidebar. Contains one or more panes.
- **Pane**: A split region within a workspace. Can be split left/right/up/down.
- **Surface**: An actual terminal or browser instance inside a pane.

### Addressing / Refs

Objects are referenced by UUID (`A1B2C3D4-...`), short ref (`workspace:1`, `pane:2`, `surface:3`), or numeric index (`0`, `1`). Use `--id-format refs|uuids|both` to control output format.

### Environment Variables

cmux sets these inside managed terminals: `CMUX_WORKSPACE_ID` (current workspace UUID, used as default for `--workspace`), `CMUX_SURFACE_ID`, `CMUX_TAB_ID`, `CMUX_SOCKET_PATH` (default: `/tmp/cmux.sock`).

### Socket Communication

Unix domain socket at `/tmp/cmux.sock`. V2 API uses newline-delimited JSON. CLI wraps socket calls into user-friendly commands.

## Quick Command Reference

### Global Flags

```
--socket PATH              Override socket path (default: /tmp/cmux.sock)
--window WINDOW            Target specific window
--password PASSWORD        Socket auth password
--json                     Output as JSON
--id-format refs|uuids|both  Control ID format
--version, -v              Show version
--help, -h                 Show help
```

### Workspace Commands

| Command                                        | Description                                               |
| ---------------------------------------------- | --------------------------------------------------------- |
| `new-workspace [--command <text>]`             | Create workspace (auto-appends `\n`). Returns `OK <uuid>` |
| `list-workspaces`                              | List all workspaces                                       |
| `select-workspace --workspace <ref>`           | Switch to workspace                                       |
| `rename-workspace [--workspace <ref>] <title>` | Rename workspace                                          |
| `close-workspace --workspace <ref>`            | Close workspace                                           |
| `current-workspace`                            | Print current workspace ID                                |

### Pane and Input Commands

| Command                                                                          | Description                   |
| -------------------------------------------------------------------------------- | ----------------------------- |
| `new-split <left\|right\|up\|down> [--workspace <ref>]`                          | Split pane                    |
| `new-surface [--type <terminal\|browser>] [--pane <ref>]`                        | Add surface                   |
| `list-panes [--workspace <ref>]`                                                 | List panes                    |
| `focus-pane --pane <ref>`                                                        | Focus pane                    |
| `close-surface [--surface <ref>]`                                                | Close surface                 |
| `send [--workspace <ref>] [--surface <ref>] <text>`                              | Send text (must include `\n`) |
| `send-key [--workspace <ref>] [--surface <ref>] <key>`                           | Send keystroke                |
| `read-screen [--workspace <ref>] [--surface <ref>] [--scrollback] [--lines <n>]` | Read terminal content         |

### Notification / Status Commands

| Command                                                     | Description        |
| ----------------------------------------------------------- | ------------------ |
| `notify --title <text> [--subtitle <text>] [--body <text>]` | Send notification  |
| `set-status <key> <value> [--icon <name>] [--color <hex>]`  | Set sidebar status |
| `set-progress <0.0-1.0> [--label <text>]`                   | Set progress bar   |
| `log [--level <level>] [--source <name>] <message>`         | Add log entry      |

### Browser Subsystem (Summary)

The browser subsystem has 40+ commands for full web automation. Key categories:

- **Navigation**: `browser open`, `browser navigate`/`goto`, `browser back`/`forward`/`reload`
- **Interaction**: `browser click`, `browser fill`, `browser type`, `browser select`, `browser press`
- **Inspection**: `browser snapshot [--interactive]`, `browser eval <js>`, `browser get`, `browser is`
- **Waiting**: `browser wait --selector|--text|--url-contains|--function [--timeout-ms]`
- **`--snapshot-after` flag**: Most interaction commands accept this flag to automatically capture a snapshot after the action

Load `references/cmux-reference.md` for full browser command syntax.

### Key Commands Not in Quick Reference

These are documented in the reference file:

- **`wait-for <channel>`** -- Inter-process synchronization (tmux compat)
- **`claude-hook <event>`** -- Claude Code integration hook
- **`pipe-pane`** -- Pipe pane output to external command
- **`popup`** -- Show popup overlay
- **`set-hook`** / **`bind-key`** / **`unbind-key`** -- Hook and key binding management

## Critical Gotchas

### `--command` auto-appends newline

`cmux new-workspace --command 'echo hello'` automatically appends `\n`, so the command executes immediately. Do NOT add your own `\n`.

### `send` requires explicit `\n`

Unlike `--command`, `cmux send` does NOT auto-append a newline. You must include it:

```bash
# WRONG - text is typed but not executed
cmux send --workspace "$WS" "echo hello"

# CORRECT - command executes
cmux send --workspace "$WS" $'echo hello\n'
```

### Output format: `OK <uuid>`

`cmux new-workspace` returns `OK <uuid>`. Extract the workspace ID:

```bash
WS=$(cmux new-workspace | awk '{print $2}')
```

### Shell quoting with `--command`

Use single quotes to prevent outer shell expansion of `$()`:

```bash
# CORRECT - subshell runs inside workspace
cmux new-workspace --command 'source "$(erk pr teleport 456 --new-slot --script --sync)"'

# WRONG - subshell expands in current shell
cmux new-workspace --command "source \"$(erk pr teleport 456 --new-slot --script --sync)\""
```

### No `--working-directory` CLI flag

The CLI does not expose a working directory flag. Workaround:

```bash
cmux new-workspace --command 'cd /path/to/project'
```

### Startup delay

There is a ~0.5s internal delay after workspace creation before commands are sent, to allow the shell to initialize. Keep this in mind when chaining commands.

### Workspace names are just labels

cmux knows nothing about git branches. Branch names used as workspace titles via `rename-workspace` are purely cosmetic labels for human navigation.

## Erk Integration

### Configuration

cmux integration is gated on a global config flag:

```toml
# ~/.erk/config.toml
cmux_integration = true
```

Check/set via CLI:

```bash
erk config get cmux_integration
erk config set cmux_integration true
```

### `erk exec cmux-checkout-workspace`

Creates a cmux workspace that checks out a PR and syncs with trunk:

```bash
erk exec cmux-checkout-workspace --pr 8152
erk exec cmux-checkout-workspace --pr 8152 --branch "my-branch"
```

What it does:

1. Auto-detects PR head branch via `gh pr view --json headRefName` (if `--branch` omitted)
2. Creates workspace running: `source "$(erk pr teleport <pr> --new-slot --script --sync)"`
3. Renames workspace to the branch name
4. Outputs JSON: `{"success": true, "pr_number": N, "branch": "...", "workspace_name": "..."}`

### TUI Dashboard Commands

When `cmux_integration` is enabled, the erk dash TUI command palette exposes:

- **cmux checkout** (action) -- Creates a cmux workspace for the selected plan's PR
- **copy cmux checkout** (copy) -- Copies the cmux checkout command to clipboard

Both require a plan with `pr_number` and `pr_head_branch`.

## Common Scripting Patterns

```bash
# Create workspace and run command
WS=$(cmux new-workspace --command 'cd ~/code/myproject && make build' | awk '{print $2}')
cmux rename-workspace --workspace "$WS" "build"

# Create workspace, then send commands separately
WS=$(cmux new-workspace | awk '{print $2}')
cmux send --workspace "$WS" $'cd ~/code/myproject\n'
cmux send --workspace "$WS" $'make test\n'

# Read terminal output
cmux read-screen --workspace "$WS" --lines 50
cmux read-screen --workspace "$WS" --scrollback

# Split workspace layout
WS=$(cmux new-workspace --command 'cd ~/code/project' | awk '{print $2}')
cmux new-split right --workspace "$WS"

# JSON output for scripting
cmux --json list-workspaces
cmux select-workspace --workspace workspace:0
```

## Troubleshooting

| Issue                               | Cause                      | Fix                                      |
| ----------------------------------- | -------------------------- | ---------------------------------------- |
| `Connection refused`                | cmux app not running       | Launch cmux.app                          |
| `Socket not found`                  | Wrong socket path          | Check `/tmp/cmux.sock` exists            |
| Command typed but not executed      | Missing `\n` in `send`     | Use `$'command\n'`                       |
| Wrong workspace targeted            | No `--workspace` flag      | Use `$CMUX_WORKSPACE_ID` or explicit ref |
| `--command` text expanded too early | Double quotes around `$()` | Use single quotes                        |
