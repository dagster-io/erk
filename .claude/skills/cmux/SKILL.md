---
name: cmux
description: This skill should be used when working with cmux, the terminal multiplexer application. Use when users mention cmux commands, workspace management, terminal pane operations, or cmux integration with erk. Essential for understanding cmux's workspace model, CLI commands, and scripting patterns.
---

# cmux - Terminal Multiplexer

## Overview

**cmux** is a native macOS terminal application (Swift/AppKit) that provides terminal multiplexing with workspaces, panes, and splits. It uses Ghostty's rendering engine (libghostty) for GPU-accelerated terminal output. The CLI communicates with the running app via a Unix domain socket at `/tmp/cmux.sock`.

Think of cmux as "tmux reimagined as a native macOS app" -- it has workspaces (like tmux windows), panes (like tmux panes), and surfaces (individual terminal or browser instances within panes), all controllable via a rich CLI.

## When to Use This Skill

Invoke this skill when users:

- Mention cmux commands or workspace management
- Need to script workspace creation or manipulation
- Ask about cmux integration with erk (the `cmux_integration` config flag)
- Want to automate terminal layouts or send commands to terminals
- Need to understand cmux's object model (windows > workspaces > panes > surfaces)
- Ask about the `erk exec cmux-sync-workspace` command

## Core Concepts

### Object Hierarchy

```
Window (top-level OS window)
  └── Workspace (vertical tab, like a tmux window)
        └── Pane (a split region)
              └── Surface (terminal or browser instance)
```

- **Window**: macOS application window. Multiple windows supported.
- **Workspace**: A tab in the sidebar. Contains one or more panes.
- **Pane**: A split region within a workspace. Can be split left/right/up/down.
- **Surface**: An actual terminal or browser instance inside a pane.

### Addressing / Refs

Objects can be referenced by:

| Format    | Example                              | Description   |
| --------- | ------------------------------------ | ------------- |
| UUID      | `A1B2C3D4-...`                       | Full UUID     |
| Short ref | `workspace:1`, `pane:2`, `surface:3` | Type + index  |
| Index     | `0`, `1`, `2`                        | Numeric index |

Use `--id-format refs|uuids|both` to control output format.

### Environment Variables

cmux automatically sets these inside terminals it manages:

| Variable            | Description                                                |
| ------------------- | ---------------------------------------------------------- |
| `CMUX_WORKSPACE_ID` | Current workspace UUID (used as default for `--workspace`) |
| `CMUX_SURFACE_ID`   | Current surface UUID                                       |
| `CMUX_TAB_ID`       | Current tab identifier                                     |
| `CMUX_SOCKET_PATH`  | Override socket path (default: `/tmp/cmux.sock`)           |

### Socket Communication

- Unix domain socket at `/tmp/cmux.sock`
- V2 API uses newline-delimited JSON
- CLI wraps socket calls into user-friendly commands

## Command Reference

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

| Command             | Syntax                                              | Description                                                          |
| ------------------- | --------------------------------------------------- | -------------------------------------------------------------------- |
| `new-workspace`     | `cmux new-workspace [--command <text>]`             | Create workspace. `--command` auto-appends `\n`. Returns `OK <uuid>` |
| `list-workspaces`   | `cmux list-workspaces`                              | List all workspaces                                                  |
| `select-workspace`  | `cmux select-workspace --workspace <ref>`           | Switch to workspace                                                  |
| `rename-workspace`  | `cmux rename-workspace [--workspace <ref>] <title>` | Rename workspace                                                     |
| `close-workspace`   | `cmux close-workspace --workspace <ref>`            | Close workspace                                                      |
| `current-workspace` | `cmux current-workspace`                            | Print current workspace ID                                           |

### Pane/Surface Commands

| Command         | Syntax                                                         | Description         |
| --------------- | -------------------------------------------------------------- | ------------------- |
| `new-split`     | `cmux new-split <left\|right\|up\|down> [--workspace <ref>]`   | Split pane          |
| `new-surface`   | `cmux new-surface [--type <terminal\|browser>] [--pane <ref>]` | Add surface         |
| `list-panes`    | `cmux list-panes [--workspace <ref>]`                          | List panes          |
| `focus-pane`    | `cmux focus-pane --pane <ref>`                                 | Focus pane          |
| `close-surface` | `cmux close-surface [--surface <ref>]`                         | Close surface       |
| `tree`          | `cmux tree [--all] [--workspace <ref>]`                        | Show hierarchy tree |

### Input Commands

| Command       | Syntax                                                                                | Description                              |
| ------------- | ------------------------------------------------------------------------------------- | ---------------------------------------- |
| `send`        | `cmux send [--workspace <ref>] [--surface <ref>] <text>`                              | Send text (must include `\n` to execute) |
| `send-key`    | `cmux send-key [--workspace <ref>] [--surface <ref>] <key>`                           | Send keystroke                           |
| `read-screen` | `cmux read-screen [--workspace <ref>] [--surface <ref>] [--scrollback] [--lines <n>]` | Read terminal content                    |

### Notification/Status Commands

| Command        | Syntax                                                           | Description        |
| -------------- | ---------------------------------------------------------------- | ------------------ |
| `notify`       | `cmux notify --title <text> [--subtitle <text>] [--body <text>]` | Send notification  |
| `set-status`   | `cmux set-status <key> <value> [--icon <name>] [--color <hex>]`  | Set sidebar status |
| `set-progress` | `cmux set-progress <0.0-1.0> [--label <text>]`                   | Set progress bar   |
| `log`          | `cmux log [--level <level>] [--source <name>] <message>`         | Add log entry      |

### Browser Commands

| Command            | Syntax                                  | Description        |
| ------------------ | --------------------------------------- | ------------------ |
| `browser open`     | `cmux browser open [url]`               | Open browser split |
| `browser navigate` | `cmux browser navigate <url>`           | Navigate to URL    |
| `browser click`    | `cmux browser click <selector>`         | Click element      |
| `browser snapshot` | `cmux browser snapshot [--interactive]` | Take snapshot      |

### tmux Compatibility

| Command         | Syntax                                                          | Description                  |
| --------------- | --------------------------------------------------------------- | ---------------------------- |
| `capture-pane`  | `cmux capture-pane [options]`                                   | Alias for `read-screen`      |
| `rename-window` | `cmux rename-window [--workspace <ref>] <title>`                | Alias for `rename-workspace` |
| `resize-pane`   | `cmux resize-pane --pane <ref> (-L\|-R\|-U\|-D) [--amount <n>]` | Resize pane                  |
| `swap-pane`     | `cmux swap-pane --pane <ref> --target-pane <ref>`               | Swap panes                   |
| `break-pane`    | `cmux break-pane [--workspace <ref>] [--pane <ref>]`            | Break pane to workspace      |
| `join-pane`     | `cmux join-pane --target-pane <ref>`                            | Join pane                    |

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
cmux new-workspace --command 'source "$(erk pr checkout 456 --script --sync)"'

# WRONG - subshell expands in current shell
cmux new-workspace --command "source \"$(erk pr checkout 456 --script --sync)\""
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

### `erk exec cmux-sync-workspace`

Creates a cmux workspace that checks out a PR and syncs with trunk:

```bash
erk exec cmux-sync-workspace --pr 8152
erk exec cmux-sync-workspace --pr 8152 --branch "my-branch"
```

What it does:

1. Auto-detects PR head branch via `gh pr view --json headRefName` (if `--branch` omitted)
2. Creates workspace running: `source "$(erk pr checkout <pr> --script --sync)" && gt submit --no-interactive`
3. Renames workspace to the branch name
4. Outputs JSON: `{"success": true, "pr_number": N, "branch": "...", "workspace_name": "..."}`

### TUI Dashboard Commands

When `cmux_integration` is enabled, the erk dash TUI command palette exposes:

- **cmux sync** (action) -- Creates a cmux workspace for the selected plan's PR
- **copy cmux sync** (copy) -- Copies the cmux sync command to clipboard

Both require a plan with `pr_number` and `pr_head_branch`.

### Finding and Focusing Workspaces

To find a workspace by branch name and switch to it:

```bash
# List workspaces as JSON
cmux --json list-workspaces

# Find workspace by title matching branch name, then select it
cmux select-workspace --workspace <ref>
```

## Common Scripting Patterns

### Create workspace and run command

```bash
WS=$(cmux new-workspace --command 'cd ~/code/myproject && make build' | awk '{print $2}')
cmux rename-workspace --workspace "$WS" "build"
```

### Create workspace, then send commands

```bash
WS=$(cmux new-workspace | awk '{print $2}')
cmux send --workspace "$WS" $'cd ~/code/myproject\n'
cmux send --workspace "$WS" $'make test\n'
cmux rename-workspace --workspace "$WS" "tests"
```

### Read terminal output

```bash
cmux read-screen --workspace "$WS" --lines 50
cmux read-screen --workspace "$WS" --scrollback  # include scrollback buffer
```

### Split workspace and set up layout

```bash
WS=$(cmux new-workspace --command 'cd ~/code/project' | awk '{print $2}')
cmux new-split right --workspace "$WS"
# Now workspace has two panes side by side
```

### List and select workspaces

```bash
# Plain text
cmux list-workspaces

# JSON for scripting
cmux --json list-workspaces

# Switch to workspace
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
