# cmux Complete Command Reference

Comprehensive reference for all cmux CLI commands. Load this when you need exact syntax for less-common commands. For mental model, common patterns, and gotchas, see the main `SKILL.md`.

## Global Flags

Available on all commands:

```
--socket PATH              Override socket path (default: /tmp/cmux.sock)
--window WINDOW            Target specific window
--password PASSWORD        Socket auth password
--json                     Output as JSON
--id-format refs|uuids|both  Control ID format in output
--version, -v              Show version
--help, -h                 Show help
```

## Workspace Commands

| Command             | Syntax                                                    | Description                                                          |
| ------------------- | --------------------------------------------------------- | -------------------------------------------------------------------- |
| `new-workspace`     | `cmux new-workspace [--command <text>]`                   | Create workspace. `--command` auto-appends `\n`. Returns `OK <uuid>` |
| `list-workspaces`   | `cmux list-workspaces`                                    | List all workspaces                                                  |
| `select-workspace`  | `cmux select-workspace --workspace <ref>`                 | Switch to workspace                                                  |
| `rename-workspace`  | `cmux rename-workspace [--workspace <ref>] <title>`       | Rename workspace                                                     |
| `close-workspace`   | `cmux close-workspace --workspace <ref>`                  | Close workspace                                                      |
| `current-workspace` | `cmux current-workspace`                                  | Print current workspace ID                                           |
| `reorder-workspace` | `cmux reorder-workspace --workspace <ref> --position <n>` | Reorder workspace in sidebar                                         |

## Window Management

| Command                    | Syntax                                                           | Description                          |
| -------------------------- | ---------------------------------------------------------------- | ------------------------------------ |
| `list-windows`             | `cmux list-windows`                                              | List all application windows         |
| `current-window`           | `cmux current-window`                                            | Print current window ID              |
| `new-window`               | `cmux new-window`                                                | Create a new application window      |
| `focus-window`             | `cmux focus-window --window <ref>`                               | Focus/bring window to front          |
| `close-window`             | `cmux close-window --window <ref>`                               | Close a window                       |
| `move-workspace-to-window` | `cmux move-workspace-to-window --workspace <ref> --window <ref>` | Move workspace to a different window |

## Pane Commands

| Command          | Syntax                                                       | Description             |
| ---------------- | ------------------------------------------------------------ | ----------------------- |
| `new-split`      | `cmux new-split <left\|right\|up\|down> [--workspace <ref>]` | Split pane in direction |
| `list-panes`     | `cmux list-panes [--workspace <ref>]`                        | List panes in workspace |
| `focus-pane`     | `cmux focus-pane --pane <ref>`                               | Focus a pane            |
| `list-panels`    | `cmux list-panels [--workspace <ref>]`                       | List panels             |
| `focus-panel`    | `cmux focus-panel --panel <ref>`                             | Focus a panel           |
| `send-panel`     | `cmux send-panel --panel <ref> <text>`                       | Send text to panel      |
| `send-key-panel` | `cmux send-key-panel --panel <ref> <key>`                    | Send keystroke to panel |

## Surface Commands

| Command                 | Syntax                                                               | Description                        |
| ----------------------- | -------------------------------------------------------------------- | ---------------------------------- |
| `new-surface`           | `cmux new-surface [--type <terminal\|browser>] [--pane <ref>]`       | Add surface to pane                |
| `close-surface`         | `cmux close-surface [--surface <ref>]`                               | Close a surface                    |
| `list-pane-surfaces`    | `cmux list-pane-surfaces [--pane <ref>]`                             | List surfaces in a pane            |
| `move-surface`          | `cmux move-surface --surface <ref> --target-pane <ref>`              | Move surface to another pane       |
| `reorder-surface`       | `cmux reorder-surface --surface <ref> --position <n>`                | Reorder surface within pane        |
| `drag-surface-to-split` | `cmux drag-surface-to-split --surface <ref> <left\|right\|up\|down>` | Drag surface to create a new split |
| `refresh-surfaces`      | `cmux refresh-surfaces [--workspace <ref>]`                          | Refresh all surfaces               |
| `surface-health`        | `cmux surface-health [--surface <ref>]`                              | Check surface health status        |
| `trigger-flash`         | `cmux trigger-flash [--surface <ref>]`                               | Trigger visual flash on surface    |

## Input Commands

| Command       | Syntax                                                                                | Description                              |
| ------------- | ------------------------------------------------------------------------------------- | ---------------------------------------- |
| `send`        | `cmux send [--workspace <ref>] [--surface <ref>] <text>`                              | Send text (must include `\n` to execute) |
| `send-key`    | `cmux send-key [--workspace <ref>] [--surface <ref>] <key>`                           | Send keystroke                           |
| `read-screen` | `cmux read-screen [--workspace <ref>] [--surface <ref>] [--scrollback] [--lines <n>]` | Read terminal content                    |

## Tab Commands

| Command      | Syntax                                         | Description        |
| ------------ | ---------------------------------------------- | ------------------ |
| `tab-action` | `cmux tab-action <action> [--workspace <ref>]` | Perform tab action |
| `rename-tab` | `cmux rename-tab [--workspace <ref>] <title>`  | Rename a tab       |

## Notification / Status / Sidebar Commands

| Command          | Syntax                                                           | Description                   |
| ---------------- | ---------------------------------------------------------------- | ----------------------------- |
| `notify`         | `cmux notify --title <text> [--subtitle <text>] [--body <text>]` | Send macOS notification       |
| `set-status`     | `cmux set-status <key> <value> [--icon <name>] [--color <hex>]`  | Set sidebar status item       |
| `clear-status`   | `cmux clear-status [<key>]`                                      | Clear sidebar status item(s)  |
| `list-status`    | `cmux list-status`                                               | List all sidebar status items |
| `set-progress`   | `cmux set-progress <0.0-1.0> [--label <text>]`                   | Set progress bar              |
| `clear-progress` | `cmux clear-progress`                                            | Clear progress bar            |
| `log`            | `cmux log [--level <level>] [--source <name>] <message>`         | Add sidebar log entry         |
| `list-log`       | `cmux list-log`                                                  | List sidebar log entries      |
| `clear-log`      | `cmux clear-log`                                                 | Clear sidebar log entries     |
| `sidebar-state`  | `cmux sidebar-state`                                             | Query current sidebar state   |

## Browser Commands

The browser subsystem provides a comprehensive automation API for WKWebView-based browser surfaces. Most interaction commands support the `--snapshot-after` flag to automatically capture a snapshot after the action completes.

### Navigation

| Command              | Syntax                                                                      | Description                                |
| -------------------- | --------------------------------------------------------------------------- | ------------------------------------------ |
| `browser open`       | `cmux browser open [url] [--workspace <ref>]`                               | Open browser surface (optionally with URL) |
| `browser open-split` | `cmux browser open-split [url] [--workspace <ref>] <left\|right\|up\|down>` | Open browser in a new split                |
| `browser navigate`   | `cmux browser navigate <url> [--surface <ref>]`                             | Navigate to URL (alias: `goto`)            |
| `browser goto`       | `cmux browser goto <url> [--surface <ref>]`                                 | Navigate to URL (alias for `navigate`)     |
| `browser back`       | `cmux browser back [--surface <ref>]`                                       | Navigate back                              |
| `browser forward`    | `cmux browser forward [--surface <ref>]`                                    | Navigate forward                           |
| `browser reload`     | `cmux browser reload [--surface <ref>]`                                     | Reload current page                        |

### Snapshots and Inspection

| Command            | Syntax                                                      | Description                                           |
| ------------------ | ----------------------------------------------------------- | ----------------------------------------------------- |
| `browser snapshot` | `cmux browser snapshot [--surface <ref>] [--interactive]`   | Take accessibility snapshot                           |
| `browser get`      | `cmux browser get <attribute> <selector> [--surface <ref>]` | Get element attribute value                           |
| `browser is`       | `cmux browser is <state> <selector> [--surface <ref>]`      | Check element state (visible, enabled, checked, etc.) |
| `browser identify` | `cmux browser identify <selector> [--surface <ref>]`        | Identify element details                              |

### Element Interaction

All interaction commands support `--snapshot-after` to capture a snapshot after the action.

| Command                    | Syntax                                                                  | Description              |
| -------------------------- | ----------------------------------------------------------------------- | ------------------------ |
| `browser click`            | `cmux browser click <selector> [--snapshot-after] [--surface <ref>]`    | Click element            |
| `browser dblclick`         | `cmux browser dblclick <selector> [--snapshot-after] [--surface <ref>]` | Double-click element     |
| `browser hover`            | `cmux browser hover <selector> [--snapshot-after] [--surface <ref>]`    | Hover over element       |
| `browser focus`            | `cmux browser focus <selector> [--snapshot-after] [--surface <ref>]`    | Focus element            |
| `browser check`            | `cmux browser check <selector> [--snapshot-after] [--surface <ref>]`    | Check checkbox           |
| `browser uncheck`          | `cmux browser uncheck <selector> [--snapshot-after] [--surface <ref>]`  | Uncheck checkbox         |
| `browser scroll-into-view` | `cmux browser scroll-into-view <selector> [--surface <ref>]`            | Scroll element into view |

### Form Input

| Command           | Syntax                                                                        | Description                             |
| ----------------- | ----------------------------------------------------------------------------- | --------------------------------------- |
| `browser type`    | `cmux browser type <selector> <text> [--snapshot-after] [--surface <ref>]`    | Type text into element (appends)        |
| `browser fill`    | `cmux browser fill <selector> <text> [--snapshot-after] [--surface <ref>]`    | Fill element (clears first, then types) |
| `browser select`  | `cmux browser select <selector> <value> [--snapshot-after] [--surface <ref>]` | Select dropdown option by value         |
| `browser press`   | `cmux browser press <key> [--snapshot-after] [--surface <ref>]`               | Press key                               |
| `browser keydown` | `cmux browser keydown <key> [--surface <ref>]`                                | Key down event                          |
| `browser keyup`   | `cmux browser keyup <key> [--surface <ref>]`                                  | Key up event                            |

### Element Finding

These commands locate elements using various strategies and return selectors.

| Command                    | Syntax                                          | Description                   |
| -------------------------- | ----------------------------------------------- | ----------------------------- |
| `browser find role`        | `cmux browser find role <role> [--name <text>]` | Find by ARIA role             |
| `browser find text`        | `cmux browser find text <text>`                 | Find by text content          |
| `browser find label`       | `cmux browser find label <text>`                | Find by label                 |
| `browser find placeholder` | `cmux browser find placeholder <text>`          | Find by placeholder text      |
| `browser find testid`      | `cmux browser find testid <id>`                 | Find by data-testid attribute |
| `browser find first`       | `cmux browser find first <selector>`            | Find first matching element   |
| `browser find last`        | `cmux browser find last <selector>`             | Find last matching element    |
| `browser find nth`         | `cmux browser find nth <selector> <n>`          | Find nth matching element     |

### JavaScript

| Command        | Syntax                                             | Description                    |
| -------------- | -------------------------------------------------- | ------------------------------ |
| `browser eval` | `cmux browser eval <expression> [--surface <ref>]` | Evaluate JavaScript expression |

### Waiting

| Command        | Syntax                                          | Description        |
| -------------- | ----------------------------------------------- | ------------------ |
| `browser wait` | `cmux browser wait [options] [--surface <ref>]` | Wait for condition |

Wait options (use one):

- `--selector <sel>` -- Wait for element to appear
- `--text <text>` -- Wait for text to appear on page
- `--url-contains <text>` -- Wait for URL to contain text
- `--function <js>` -- Wait for JavaScript function to return truthy
- `--timeout-ms <ms>` -- Maximum wait time (default varies)

### Frames

| Command         | Syntax                                                 | Description             |
| --------------- | ------------------------------------------------------ | ----------------------- |
| `browser frame` | `cmux browser frame <name-or-index> [--surface <ref>]` | Switch to frame context |

### Dialogs

| Command                  | Syntax                                                             | Description                          |
| ------------------------ | ------------------------------------------------------------------ | ------------------------------------ |
| `browser dialog accept`  | `cmux browser dialog accept [--text <response>] [--surface <ref>]` | Accept dialog (alert/confirm/prompt) |
| `browser dialog dismiss` | `cmux browser dialog dismiss [--surface <ref>]`                    | Dismiss dialog                       |

### Downloads

| Command                 | Syntax                                                             | Description                   |
| ----------------------- | ------------------------------------------------------------------ | ----------------------------- |
| `browser download wait` | `cmux browser download wait [--timeout-ms <ms>] [--surface <ref>]` | Wait for download to complete |

### Cookies and Storage

| Command                         | Syntax                                                                             | Description              |
| ------------------------------- | ---------------------------------------------------------------------------------- | ------------------------ |
| `browser cookies get`           | `cmux browser cookies get [--name <name>] [--surface <ref>]`                       | Get cookies              |
| `browser cookies set`           | `cmux browser cookies set --name <n> --value <v> [--domain <d>] [--surface <ref>]` | Set a cookie             |
| `browser cookies clear`         | `cmux browser cookies clear [--surface <ref>]`                                     | Clear all cookies        |
| `browser storage local get`     | `cmux browser storage local get [--key <k>] [--surface <ref>]`                     | Get localStorage value   |
| `browser storage local set`     | `cmux browser storage local set --key <k> --value <v> [--surface <ref>]`           | Set localStorage value   |
| `browser storage local clear`   | `cmux browser storage local clear [--surface <ref>]`                               | Clear localStorage       |
| `browser storage session get`   | `cmux browser storage session get [--key <k>] [--surface <ref>]`                   | Get sessionStorage value |
| `browser storage session set`   | `cmux browser storage session set --key <k> --value <v> [--surface <ref>]`         | Set sessionStorage value |
| `browser storage session clear` | `cmux browser storage session clear [--surface <ref>]`                             | Clear sessionStorage     |

### Tab Management (Browser)

| Command              | Syntax                                               | Description           |
| -------------------- | ---------------------------------------------------- | --------------------- |
| `browser tab new`    | `cmux browser tab new [url] [--surface <ref>]`       | Open new browser tab  |
| `browser tab list`   | `cmux browser tab list [--surface <ref>]`            | List browser tabs     |
| `browser tab switch` | `cmux browser tab switch <index> [--surface <ref>]`  | Switch to browser tab |
| `browser tab close`  | `cmux browser tab close [<index>] [--surface <ref>]` | Close browser tab     |

### Console and Errors

| Command                 | Syntax                                         | Description            |
| ----------------------- | ---------------------------------------------- | ---------------------- |
| `browser console list`  | `cmux browser console list [--surface <ref>]`  | List console messages  |
| `browser console clear` | `cmux browser console clear [--surface <ref>]` | Clear console messages |
| `browser errors list`   | `cmux browser errors list [--surface <ref>]`   | List JavaScript errors |
| `browser errors clear`  | `cmux browser errors clear [--surface <ref>]`  | Clear error list       |

### Visual

| Command             | Syntax                                                                 | Description                |
| ------------------- | ---------------------------------------------------------------------- | -------------------------- |
| `browser highlight` | `cmux browser highlight <selector> [--surface <ref>]`                  | Highlight element visually |
| `browser viewport`  | `cmux browser viewport [--width <n>] [--height <n>] [--surface <ref>]` | Set/get viewport size      |

### State Persistence

| Command              | Syntax                                             | Description                                 |
| -------------------- | -------------------------------------------------- | ------------------------------------------- |
| `browser state save` | `cmux browser state save <name> [--surface <ref>]` | Save browser state (cookies, storage, etc.) |
| `browser state load` | `cmux browser state load <name> [--surface <ref>]` | Load saved browser state                    |

### Scripts and Styles

| Command                 | Syntax                                              | Description                          |
| ----------------------- | --------------------------------------------------- | ------------------------------------ |
| `browser addinitscript` | `cmux browser addinitscript <js> [--surface <ref>]` | Add script to run on every page load |
| `browser addscript`     | `cmux browser addscript <js> [--surface <ref>]`     | Inject script into current page      |
| `browser addstyle`      | `cmux browser addstyle <css> [--surface <ref>]`     | Inject CSS into current page         |

### Advanced / Platform-Limited

These commands may have limited functionality on WKWebView compared to Chromium-based browsers.

| Command               | Syntax                                                           | Description                  |
| --------------------- | ---------------------------------------------------------------- | ---------------------------- |
| `browser geolocation` | `cmux browser geolocation --lat <n> --lon <n> [--surface <ref>]` | Set geolocation override     |
| `browser offline`     | `cmux browser offline [--enabled <bool>] [--surface <ref>]`      | Toggle offline mode          |
| `browser trace`       | `cmux browser trace <start\|stop> [--surface <ref>]`             | Start/stop performance trace |
| `browser network`     | `cmux browser network [--surface <ref>]`                         | Network monitoring           |
| `browser screencast`  | `cmux browser screencast <start\|stop> [--surface <ref>]`        | Start/stop screencast        |
| `browser input`       | `cmux browser input <action> [--surface <ref>]`                  | Low-level input simulation   |

## tmux Compatibility Layer

Commands that mirror tmux equivalents for users transitioning from tmux.

### Direct Aliases

| Command         | Syntax                                           | cmux Equivalent    |
| --------------- | ------------------------------------------------ | ------------------ |
| `capture-pane`  | `cmux capture-pane [options]`                    | `read-screen`      |
| `rename-window` | `cmux rename-window [--workspace <ref>] <title>` | `rename-workspace` |

### Pane Operations

| Command        | Syntax                                                          | Description                   |
| -------------- | --------------------------------------------------------------- | ----------------------------- |
| `resize-pane`  | `cmux resize-pane --pane <ref> (-L\|-R\|-U\|-D) [--amount <n>]` | Resize pane in direction      |
| `swap-pane`    | `cmux swap-pane --pane <ref> --target-pane <ref>`               | Swap two panes                |
| `break-pane`   | `cmux break-pane [--workspace <ref>] [--pane <ref>]`            | Break pane into new workspace |
| `join-pane`    | `cmux join-pane --target-pane <ref>`                            | Join pane into another        |
| `respawn-pane` | `cmux respawn-pane [--pane <ref>] [--command <text>]`           | Restart pane process          |

### Window/Navigation

| Command           | Syntax                               | Description                     |
| ----------------- | ------------------------------------ | ------------------------------- |
| `next-window`     | `cmux next-window`                   | Switch to next workspace        |
| `previous-window` | `cmux previous-window`               | Switch to previous workspace    |
| `last-window`     | `cmux last-window`                   | Switch to last active workspace |
| `last-pane`       | `cmux last-pane [--workspace <ref>]` | Switch to last active pane      |
| `find-window`     | `cmux find-window <pattern>`         | Find workspace by name pattern  |

### Buffer/Copy Mode

| Command        | Syntax                                | Description              |
| -------------- | ------------------------------------- | ------------------------ |
| `copy-mode`    | `cmux copy-mode [--surface <ref>]`    | Enter copy mode          |
| `set-buffer`   | `cmux set-buffer <text>`              | Set paste buffer content |
| `list-buffers` | `cmux list-buffers`                   | List paste buffers       |
| `paste-buffer` | `cmux paste-buffer [--surface <ref>]` | Paste from buffer        |

### History

| Command         | Syntax                                 | Description              |
| --------------- | -------------------------------------- | ------------------------ |
| `clear-history` | `cmux clear-history [--surface <ref>]` | Clear scrollback history |

### Hooks and Keys

| Command      | Syntax                                | Description              |
| ------------ | ------------------------------------- | ------------------------ |
| `set-hook`   | `cmux set-hook <hook-name> <command>` | Set hook to run on event |
| `bind-key`   | `cmux bind-key <key> <command>`       | Bind key to command      |
| `unbind-key` | `cmux unbind-key <key>`               | Unbind key               |

### Pipe and Sync

| Command     | Syntax                                    | Description                                     |
| ----------- | ----------------------------------------- | ----------------------------------------------- |
| `pipe-pane` | `cmux pipe-pane [--pane <ref>] <command>` | Pipe pane output to command                     |
| `wait-for`  | `cmux wait-for <channel>`                 | Wait for signal on channel (inter-process sync) |

### Display

| Command           | Syntax                                                       | Description            |
| ----------------- | ------------------------------------------------------------ | ---------------------- |
| `popup`           | `cmux popup [--width <n>] [--height <n>] [--command <text>]` | Show popup overlay     |
| `display-message` | `cmux display-message <text>`                                | Display status message |

## Utility / Diagnostic Commands

| Command               | Syntax                                     | Description                  |
| --------------------- | ------------------------------------------ | ---------------------------- |
| `ping`                | `cmux ping`                                | Check if cmux is running     |
| `capabilities`        | `cmux capabilities`                        | List supported capabilities  |
| `identify`            | `cmux identify [--surface <ref>]`          | Identify surface details     |
| `claude-hook`         | `cmux claude-hook <event> [--data <json>]` | Claude Code integration hook |
| `set-app-focus`       | `cmux set-app-focus [--focused <bool>]`    | Set app focus state          |
| `simulate-app-active` | `cmux simulate-app-active`                 | Simulate app becoming active |

## Workflow Patterns

### Browser Automation: Navigate and Fill Form

```bash
# Open browser, navigate, fill form
cmux browser open "https://example.com/login" --workspace "$WS"
cmux browser fill "input[name=email]" "user@example.com" --snapshot-after
cmux browser fill "input[name=password]" "secret" --snapshot-after
cmux browser click "button[type=submit]" --snapshot-after
cmux browser wait --url-contains "/dashboard"
```

### Browser Automation: Scrape Content

```bash
# Navigate and extract data
cmux browser navigate "https://example.com/data"
cmux browser wait --selector ".results-table"
cmux browser eval "document.querySelector('.results-table').innerText"
```

### Layout Scripting: Multi-Pane Development Setup

```bash
WS=$(cmux new-workspace --command 'cd ~/code/project' | awk '{print $2}')
cmux rename-workspace --workspace "$WS" "dev"

# Create right split for tests
cmux new-split right --workspace "$WS"

# Send commands to specific panes
PANES=$(cmux --json list-panes --workspace "$WS")
cmux send --surface surface:0 $'make watch\n'
cmux send --surface surface:1 $'make test --watch\n'
```

### Inter-Process Synchronization with wait-for

```bash
# Terminal 1: Wait for signal
cmux wait-for "build-done"

# Terminal 2: Signal when build completes
make build && cmux send-key --surface <ref> "build-done"
```

### Notification Workflow: Long-Running Task

```bash
cmux set-status "build" "running" --icon "hammer" --color "#FFA500"
cmux set-progress 0.0 --label "Building..."

# ... task runs ...

cmux set-progress 1.0 --label "Complete"
cmux clear-progress
cmux set-status "build" "done" --icon "checkmark" --color "#00FF00"
cmux notify --title "Build Complete" --body "Project built successfully"
```

### Claude Code Integration

```bash
# Register a hook for Claude Code events
cmux claude-hook "session-start" --data '{"session_id": "abc123"}'
```
