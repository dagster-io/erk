---
title: Plugin Hook Output Bug
read_when:
  - 'plugin hooks show "Callback hook succeeded: Success" but no output'
  - "debugging plugin hooks that run but don't display output"
  - troubleshooting UserPromptSubmit hooks in plugins
---

# Plugin Hook Output Bug

> **Known Bug**: Plugin hooks execute but their stdout/stderr output is not captured or displayed.

## Issue Tracking

- **GitHub Issue**: [anthropics/claude-code#12151](https://github.com/anthropics/claude-code/issues/12151)
- **Status**: Open (as of December 2025)

## Symptoms

When running hooks defined in a plugin's `hooks/hooks.json`:

- Hook executes successfully (can confirm via side effects like file writes)
- Claude Code shows: `Callback hook succeeded: Success`
- **Actual hook output (stdout/stderr) is NOT displayed**

## Root Cause

The plugin hook execution pipeline in Claude Code doesn't capture or relay stdout/stderr from plugin-defined hooks back to the user.

## What Works vs What Doesn't

| Location                      | Output Captured? |
| ----------------------------- | ---------------- |
| `.claude/settings.json` hooks | Yes              |
| Plugin `hooks/hooks.json`     | No (bug)         |

The same hook definition works correctly when placed in `.claude/settings.json` but fails to show output when defined in a plugin's `hooks/hooks.json`.

## Workarounds

### Option 1: Use `erk kit install` (Recommended)

ERK kits work around this by writing hooks directly to `.claude/settings.json` during installation:

```bash
erk kit install <kit-name>
```

This bypasses the plugin hook system entirely.

### Option 2: Define Hooks in settings.json

Manually move hook definitions from plugin `hooks/hooks.json` to `.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "your-hook-command",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

### Option 3: Use Side Effects

If you must use plugin hooks, rely on side effects rather than output:

- Write to files instead of stdout
- Use exit codes for success/failure signaling
- Return JSON with `systemMessage` field (may work in some contexts)

## Testing If Your Hook Runs

To verify a plugin hook is executing despite no output:

```bash
# In your hook script, write to a file
echo "Hook ran at $(date)" >> /tmp/hook-debug.log
```

If the log file updates, your hook is running - the output just isn't being captured.
