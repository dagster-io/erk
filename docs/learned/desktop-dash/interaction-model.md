---
title: Desktop Dashboard Interaction Model
read_when:
  - "designing new erkdesk UX features"
  - "deciding whether to port a TUI feature to the desktop dashboard"
  - "adding action discovery mechanisms (context menus, shortcuts)"
  - "planning notification or badge features for erkdesk"
tripwires:
  - action: "porting a TUI modal or overlay to erkdesk"
    warning: "The right pane (WebContentsView showing live GitHub) replaces all TUI modals. Don't build detail modals — the embedded GitHub page provides richer context than any custom UI."
  - action: "requiring keyboard shortcuts for actions"
    warning: "Erkdesk uses discoverability-first design. Toolbar buttons and (future) context menus are primary. Keyboard shortcuts are secondary convenience, not required paths."
  - action: "designing notification features"
    warning: "Notification/badge system is planned but NOT implemented. Don't assume infrastructure exists for state-diff detection, OS notifications, or row badges."
---

# Desktop Dashboard Interaction Model

Erkdesk is NOT a 1:1 port of the TUI. The desktop medium inverts the information hierarchy, replaces memorized shortcuts with discoverable GUI elements, and opens up notification-driven workflows. This document captures the design rationale — the _why_ behind each divergence from TUI patterns.

## The Core Insight: Different Affordances Demand Different Design

The TUI operates under terminal constraints: single viewport (~80x24), keyboard-only input, no persistent state between screens, and modal overlays for detail. The desktop dashboard has a large persistent viewport (~1920x1080), mouse+keyboard input, simultaneous views, and OS-level notification capabilities.

**Porting TUI features 1:1 would waste desktop affordances and create a worse experience.** Every feature decision should ask: "What does the desktop medium make possible that the terminal couldn't do?"

## Inverted Hierarchy: Right Pane is Primary

The most important architectural divergence from the TUI.

**TUI pattern:** The plan table is the primary workspace. Details appear as temporary modal overlays (triggered by Enter), then disappear on Esc. The user's attention is on the table.

**Desktop pattern:** The plan table is a _navigation sidebar_. The right pane — a native Electron `WebContentsView` showing live GitHub pages — is the primary workspace. The user's attention is on the right pane.

<!-- Source: erkdesk/src/renderer/components/SplitPane.tsx, split-pane layout -->
<!-- Source: erkdesk/src/main/index.ts, WebContentsView setup -->

This inversion has cascading design implications:

1. **No detail modal.** The right pane shows the full GitHub PR interface (diffs, comment threads, check runs, merge status) — far richer than any custom modal could be. Building a modal would be redundant.
2. **Narrow left pane.** The table is sidebar-width, not full-screen. It exists for selection, not consumption.
3. **Contextual actions follow selection.** The toolbar enables/disables buttons based on what's selected, because the user is acting on what the right pane shows.
4. **PR URL takes priority over issue URL.** When both exist, the right pane loads the PR because PRs are more actionable (reviews, checks, merge). This is a UX decision documented in App.tsx's URL-loading effect.

## Discoverability Over Memorization

The TUI uses two layers of memorized keyboard shortcuts — one set for the main table, a different set inside the detail modal. This works because keyboard is the only input method and power users build muscle memory.

In a desktop app, this pattern fails:

- Mouse is available and expected
- Discoverability beats memorization — users expect to see available actions
- Context menus and toolbars are standard desktop conventions

**Erkdesk's approach:** A data-driven toolbar where each action declares an `isAvailable` predicate. Buttons visually disable when unavailable, making the action space self-documenting. See the action-toolbar doc for the full predicate table and data-driven pattern.

<!-- Source: erkdesk/src/renderer/components/ActionToolbar.tsx, ACTIONS array -->

**Future expansion:** Right-click context menus and a command palette are planned but not yet implemented. The design principle: GUI elements are the primary action path; keyboard shortcuts are secondary convenience added only for high-frequency actions.

## Notification-Driven Workflow (Planned, Not Implemented)

The TUI requires visual polling — the user manually refreshes, scans rows for status changes, and notices differences. This demands active attention and misses changes between refreshes.

The desktop medium enables passive monitoring through:

- **Row badges** indicating state changes since last selection (e.g., checks completed, new review comments)
- **OS-level notifications** for high-priority events (CI pass, new reviews)
- **State diffing** — comparing previous refresh data against new data to detect what changed

**Current state:** Auto-refresh (15-second interval) exists but without change detection or notifications. The infrastructure for state diffing and OS notifications hasn't been built.

## Decision Table: TUI vs Desktop Pattern Selection

| Design Decision   | TUI Approach               | Desktop Approach                         | Why the Divergence                          |
| ----------------- | -------------------------- | ---------------------------------------- | ------------------------------------------- |
| Detail view       | Modal overlay (temporary)  | Right pane with live GitHub (persistent) | Desktop has space for side-by-side views    |
| Action discovery  | Memorized shortcuts        | Visible toolbar buttons                  | Mouse availability enables discoverability  |
| State awareness   | Visual scanning on refresh | Badges + OS notifications (planned)      | Desktop apps can notify passively           |
| Primary workspace | Plan table (full screen)   | Right pane (embedded GitHub)             | Large viewport inverts the hierarchy        |
| Navigation        | Keyboard only (j/k)        | Mouse + keyboard (j/k preserved)         | Desktop adds mouse, doesn't remove keyboard |

## Design Principles

1. **Don't fight desktop conventions.** Toolbars, context menus, mouse interaction, and OS notifications are expected. Don't force terminal UX patterns onto a desktop app.

2. **Maximize information density.** The large viewport allows side-by-side plan list + full GitHub page + always-visible toolbar. Use the space — don't artificially constrain the UI to look like a terminal.

3. **Right pane is the star.** The embedded GitHub view is the unique value proposition: no context switching to browser, PR/issue/run visible in-app, contextual actions based on what you're viewing. New features should enhance the right pane experience, not compete with it.

4. **Progressive enhancement for power users.** Start with discoverable GUI elements. Add keyboard shortcuts and a command palette only when usage patterns justify them.

## Related Documentation

- [Action Toolbar](action-toolbar.md) — Data-driven action definitions and availability predicates
- [App Architecture](app-architecture.md) — State management, WebView overlay, auto-refresh
- [Framework Evaluation](framework-evaluation.md) — Why Electron was chosen
- [Backend Communication](backend-communication.md) — How Electron talks to Python
