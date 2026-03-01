# Plan: Improve cmux Skill

## Context

The existing cmux skill at `.claude/skills/cmux/SKILL.md` covers core concepts and common operations well, but has significant gaps when compared against the full `cmux --help` output. The browser subsystem alone has 40+ subcommands but only 4 are documented. Several entire command categories (window management, panels, sidebar state queries) are missing entirely. Additionally, the `tree` command is listed in the skill but doesn't appear in the help text (possibly removed).

The skill is already 307 lines. Adding comprehensive coverage of all missing commands inline would bloat it beyond usefulness. The fix: move the complete command reference into a `references/` file, keeping `SKILL.md` focused on mental model, common operations, and when-to-load-references guidance.

## Changes

### 1. Create `references/cmux-reference.md` — Complete command reference

Move the detailed command tables out of SKILL.md and into a comprehensive reference file covering **all** commands from `cmux --help`. Organize by category:

**New/missing sections to add:**

- **Window Management**: `list-windows`, `current-window`, `new-window`, `focus-window`, `close-window`, `move-workspace-to-window`
- **Surface Management**: `move-surface`, `reorder-surface`, `drag-surface-to-split`, `refresh-surfaces`, `surface-health`, `trigger-flash`, `list-pane-surfaces`
- **Panel Commands**: `list-panels`, `focus-panel`, `send-panel`, `send-key-panel`
- **Tab Commands**: `tab-action`, `rename-tab`, `reorder-workspace`
- **Sidebar Metadata** (complete): Add `clear-status`, `list-status`, `clear-progress`, `clear-log`, `list-log`, `sidebar-state`
- **Browser Commands** (comprehensive): All 40+ subcommands organized into subcategories:
  - Navigation (open, open-split, navigate/goto, back/forward/reload)
  - Snapshots & Inspection (snapshot, get, is, identify)
  - Element Interaction (click, dblclick, hover, focus, check/uncheck, scroll-into-view)
  - Form Input (type, fill, select, press/keydown/keyup)
  - Element Finding (find by role/text/label/placeholder/testid/first/last/nth)
  - JavaScript (eval)
  - Waiting (wait with --selector/--text/--url-contains/--function/--timeout-ms)
  - Frames (frame)
  - Dialogs (dialog accept/dismiss)
  - Downloads (download wait)
  - Cookies & Storage (cookies get/set/clear, storage local/session get/set/clear)
  - Tab Management (tab new/list/switch/close)
  - Console & Errors (console list/clear, errors list/clear)
  - Visual (highlight, viewport)
  - State Persistence (state save/load)
  - Scripts & Styles (addinitscript, addscript, addstyle)
  - Advanced/Platform-limited (geolocation, offline, trace, network, screencast, input) — note WKWebView limitations
  - `--snapshot-after` flag pattern (available on most interaction commands)
- **tmux Compatibility** (complete): Add `pipe-pane`, `wait-for`, `next-window`, `previous-window`, `last-window`, `last-pane`, `find-window`, `clear-history`, `set-hook`, `popup`, `bind-key`, `unbind-key`, `copy-mode`, `set-buffer`, `list-buffers`, `paste-buffer`, `respawn-pane`, `display-message`
- **Utility/Diagnostic**: `ping`, `capabilities`, `identify`, `claude-hook`, `set-app-focus`, `simulate-app-active`
- **Workflow Patterns**: Common multi-command recipes (browser automation, layout scripting, notification workflows)

### 2. Update `SKILL.md` — Streamline and fix

**Remove**: Detailed command tables (moved to reference). Remove `tree` command (not in help output).

**Keep/improve**:
- Overview, object hierarchy, addressing/refs, environment variables, socket communication
- Critical gotchas section (already excellent)
- Erk integration section
- Common scripting patterns

**Add**:
- "When to load references" section pointing to `references/cmux-reference.md`
- Brief mention of browser subsystem capabilities (pointing to reference for details)
- Brief mention of window management (pointing to reference)
- Mention of `--snapshot-after` pattern for browser commands
- `claude-hook` command for Claude Code integration
- `wait-for` for inter-process synchronization

**Fix**:
- Remove `tree` command from pane/surface table (not in help output)

## Files Modified

| File | Action |
|------|--------|
| `.claude/skills/cmux/SKILL.md` | Edit: streamline, fix errors, add reference pointers |
| `.claude/skills/cmux/references/cmux-reference.md` | Create: comprehensive command reference |

## Verification

1. Confirm all commands from `cmux --help` are documented in the reference
2. Confirm `SKILL.md` is under ~200 lines (concise for loading)
3. Confirm `references/cmux-reference.md` covers browser, tmux compat, windows, panels, tabs, sidebar fully
4. Spot-check a few commands by running them to verify syntax
