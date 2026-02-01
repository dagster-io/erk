---
title: Desktop Dashboard Interaction Model
read_when:
  - "designing the desktop dashboard UX"
  - "deciding which TUI features to carry forward to Electron"
  - "understanding the interaction model differences between TUI and desktop"
---

# Desktop Dashboard Interaction Model

The desktop dashboard is NOT a 1:1 port of the TUI. It inverts the hierarchy, uses GUI-native affordances, and embraces notification-driven workflows. This document explains why and how.

## Why Not Port TUI Features 1:1?

The TUI was optimized for terminal constraints:

- Small viewport (80x24 typical)
- Keyboard-only navigation
- No persistent visual state (screen clears)
- Modal dialogs for details

The desktop dashboard has different affordances:

- Large viewport (1920x1080 typical)
- Mouse + keyboard
- Persistent visual state
- Multiple simultaneous views

**Porting TUI features 1:1 would waste these affordances and create a worse experience.**

## Inverted Hierarchy: Right Pane is Primary

### TUI Model (Left-Focused)

In the TUI, the plan table is the primary workspace:

```
┌────────────────────────────────────┐
│  Plan Table (Primary Workspace)   │
│  ↓                                 │
│  [List of 20 plans]                │
│  j/k to navigate                   │
│  Press 'i' → Opens modal           │
└────────────────────────────────────┘

         (Modal appears on top)
┌────────────────────────────────────┐
│  Plan Detail Modal                 │
│  - Full title                      │
│  - PR description                  │
│  - Command palette                 │
│  Esc to close                      │
└────────────────────────────────────┘
```

**Pattern:** Table is primary, details are temporary overlays.

### Desktop Model (Right-Focused)

In the desktop dashboard, the right pane is the primary workspace:

```
┌──────────┬──────────────────────────┐
│ Plan     │ Right Pane               │
│ Table    │ (Primary Workspace)      │
│          │                          │
│ [20      │ [Live GitHub PR page]    │
│  plans]  │                          │
│          │ - Full PR view           │
│ j/k nav  │ - Comment threads        │
│          │ - Diff view              │
│          │ - Actions runs           │
└──────────┴──────────────────────────┘
```

**Pattern:** Table is navigation, right pane is workspace. The embedded GitHub view provides context-rich detail that far exceeds what a modal could show.

**Implications:**

1. Don't show a separate detail modal - the right pane already shows richer detail than any modal could
2. Table can be narrower (left sidebar width, not full screen)
3. User's attention is on the right pane, not the table
4. Actions should be contextual to the right pane content (toolbar appears based on selection)

## GUI-Native Actions: Discoverability Over Memorization

### TUI Model (Keyboard Shortcuts)

The TUI uses memorized keyboard shortcuts:

- `s` - submit to queue
- `i` - open issue
- `p` - open PR
- `5` - fix conflicts
- `e` - copy checkout+sync command

**Why this works in TUI:**

- Keyboard is the only input method
- Power users memorize shortcuts
- Command palette provides discovery (`Ctrl+K`)

**Why this doesn't work in desktop:**

- Mouse is available and expected
- Discoverability beats memorization for GUI apps
- Users expect right-click context menus and toolbars

### Desktop Model (GUI-Native)

The desktop dashboard uses GUI-native affordances:

**Contextual Toolbar:**

```
┌────────────────────────────────────┐
│ [Submit] [Land] [Address] [Close]  │  ← Buttons appear/disappear based on selection
└────────────────────────────────────┘
```

**Right-Click Context Menu:**

```
┌─────────────────────────┐
│ → Open Issue in Browser │
│ → Open PR in Browser    │
│ → Open Run in Browser   │
│ ─────────────────────── │
│ → Copy Checkout Command │
│ → Copy Submit Command   │
│ → Copy Replan Command   │
└─────────────────────────┘
```

**Why this is better:**

- **Discoverability:** Actions are visible, not memorized
- **Contextual availability:** Buttons gray out when unavailable
- **Standard UX:** Matches user expectations from other desktop apps
- **Mouse-friendly:** Click instead of typing keyboard shortcuts

**When to add keyboard shortcuts:**

- Add a command palette later IF users request it
- Add shortcuts for frequent actions (e.g., `Cmd+R` for refresh)
- Don't require shortcuts - GUI should be sufficient

## No Detail Modal: Right Pane Replaces It

### TUI Detail Modal

The TUI shows a modal with:

- Full plan title
- PR description
- Last implementation times
- Command palette

**Why a modal?** Terminal has one view, so details must overlay.

### Desktop Right Pane

The desktop dashboard's right pane shows:

- **Live GitHub PR page** (not just description - the full PR interface)
- All comments and threads
- Diff view with inline comments
- Actions runs and checks
- Issue view with full markdown rendering

**Why this is better:**

- Richer content (full GitHub UI vs text-only modal)
- Persistent (doesn't disappear on action)
- Native GitHub interaction (expand threads, react to comments)

**Implication:** Don't build a detail modal. The right pane already provides superior detail.

## Notification-Driven Workflow vs Visual Polling

### TUI Model (Visual Polling)

The TUI requires users to visually scan for changes:

1. User refreshes table (manual or auto-refresh)
2. User scans rows for status changes
3. User notices a check mark changed from ⟳ to ✓
4. User selects that row to investigate

**Problem:** Requires active attention. Users miss changes between refreshes.

### Desktop Model (Notification-Driven)

The desktop dashboard proactively notifies users:

**Notification Badges on Rows:**

```
┌──────────────────────────────────┐
│ #123 [!] Add dark mode           │  ← Badge indicates state changed
│ #124     Fix login bug           │
│ #125 [!] Refactor API            │  ← Badge indicates state changed
└──────────────────────────────────┘
```

**OS-Level Notifications:**

```
┌────────────────────────────────────┐
│ erk: PR #456 checks passed         │
│ All checks succeeded. Ready to land│
└────────────────────────────────────┘
```

**Notification Types:**

1. **New PR review comments** → OS notification + row badge
2. **GitHub Actions completion** → OS notification + row badge
3. **PR state change** (merged, closed) → Row badge
4. **Local Claude session idle** → OS notification + row badge

**How it works:**

1. Desktop app diffs previous state against new state on each refresh
2. Detected changes trigger notifications and badges
3. Selecting a row clears its badge (acknowledged)

**Why this is better:**

- **Passive monitoring:** App tells you when something needs attention
- **Reduces cognitive load:** Don't need to visually scan for changes
- **Timely response:** Know immediately when checks pass or comments arrive
- **Matches desktop conventions:** OS notifications are standard UX

## Comparison Table: TUI vs Desktop

| Aspect                     | TUI                                  | Desktop Dashboard                      |
| -------------------------- | ------------------------------------ | -------------------------------------- |
| **Primary workspace**      | Plan table                           | Right pane (embedded GitHub)           |
| **Detail view**            | Modal overlay                        | Right pane (persistent)                |
| **Action discovery**       | Keyboard shortcuts + command palette | Toolbar + context menu                 |
| **Navigation**             | Keyboard only (j/k)                  | Mouse + keyboard                       |
| **State change detection** | Visual scanning                      | Notification badges + OS notifications |
| **Actions**                | Memorized shortcuts                  | Discoverable GUI elements              |
| **Context richness**       | Text-only modal                      | Full GitHub UI                         |
| **Viewport**               | 80x24 typical                        | 1920x1080 typical                      |
| **Use case**               | Quick terminal-based monitoring      | Persistent command center              |

## Design Principles

### 1. Don't Fight Desktop Conventions

Users expect desktop apps to:

- Use toolbars and context menus
- Support mouse interaction
- Show notifications for background events
- Have persistent state

Don't force terminal UX patterns onto a desktop app.

### 2. Maximize Information Density

The large viewport allows:

- Side-by-side plan list + detail view
- Full GitHub pages (not just snippets)
- Toolbar always visible (no screen real estate constraints)

Use the space - don't artificially constrain the UI to look like a terminal.

### 3. Embrace Notifications

Desktop apps can notify users passively:

- OS-level notifications for completions
- Badges for state changes since last view
- Visual indicators that survive refresh

This reduces cognitive load and makes the app a true command center, not just a dashboard.

### 4. Right Pane is the Star

The embedded GitHub view is the unique value proposition:

- No context switching to browser
- See PR/issue/run in-app
- Contextual actions based on what you're viewing

Make the right pane prominent and primary.

## Implementation Priorities

### Phase 1: Get the Core Right

- Split-pane layout (resizable)
- Plan list with j/k navigation
- WebContentsView showing GitHub pages
- Row selection updates the view

**Test:** Can I navigate plans with j/k and see the PR load on the right?

### Phase 2: GUI-Native Actions

- Contextual toolbar (buttons appear/disappear)
- Right-click context menu
- Streaming output drawer for long-running actions
- Status indicators (colored dots, not emoji)

**Test:** Can I land a PR by clicking a toolbar button and see streaming output?

### Phase 3: Notifications

- Diff previous state against new state
- Badge rows with state changes since last selection
- OS notifications for GitHub Actions completions
- OS notifications for new PR comments

**Test:** Does a GitHub Action completion trigger an OS notification and badge the row?

## Related Documentation

- [TUI Architecture Overview](../tui/architecture.md) - How TUI works today
- [TUI Action Command Inventory](../tui/action-inventory.md) - Commands to port to desktop
- [Desktop Dashboard Framework Evaluation](framework-evaluation.md) - Why Electron was chosen
- [Desktop Dashboard Backend Communication](backend-communication.md) - How Electron talks to Python
