---
title: erkdesk Action Toolbar
read_when:
  - "adding new actions to the erkdesk toolbar"
  - "modifying action availability predicates"
  - "understanding how toolbar actions connect to IPC streaming"
tripwires:
  - action: "adding a new action outside the ACTIONS array"
    warning: "All actions must be entries in the ACTIONS array in ActionToolbar.tsx. Don't create standalone action definitions elsewhere."
  - action: "implementing blocking action execution"
    warning: "Actions use streaming execution via IPC (startStreamingAction). Never await or block the UI thread on action completion. App.tsx owns the streaming lifecycle."
  - action: "adding a new action without a test case"
    warning: "ActionToolbar.test.tsx tests every action's availability predicate AND generated command. New actions need both."
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
---

# erkdesk Action Toolbar

## Why Data-Driven Actions

<!-- Source: erkdesk/src/renderer/components/ActionToolbar.tsx, ActionDef interface and ACTIONS array -->

Actions are defined as an `ActionDef` array rather than individual button handlers. This design serves two purposes: (1) the `ACTIONS` array is the single source of truth for what actions exist, their availability logic, and the CLI commands they invoke, and (2) new actions require zero component changes — just a new array entry with `isAvailable` and `getCommand` functions. CSS styling applies automatically to all buttons.

See the `ActionDef` interface and `ACTIONS` array in `erkdesk/src/renderer/components/ActionToolbar.tsx`.

## Availability Predicates

Each action gates on specific `PlanRow` fields. This table captures which fields matter and why:

| Action        | Gates On                                  | Why                                      |
| ------------- | ----------------------------------------- | ---------------------------------------- |
| Submit        | `issue_url !== null`                      | Needs an issue to submit to the queue    |
| Land          | `pr_number` + `pr_state=OPEN` + `run_url` | Can only land open PRs with completed CI |
| Address       | `pr_number !== null`                      | Review comments live on the PR           |
| Fix Conflicts | `pr_number !== null`                      | Conflicts are a PR-level concern         |
| Close         | Always available                          | Can close any plan regardless of state   |

**Land is the strictest** — it's the only action requiring three conditions. This prevents landing PRs that are already merged/closed or haven't run CI. If `run_url` is null, the PR hasn't had a workflow run yet.

## Cross-Component Streaming Boundary

The toolbar and App.tsx have a deliberate ownership split for action execution:

<!-- Source: erkdesk/src/renderer/components/ActionToolbar.tsx, handleClick callback -->
<!-- Source: erkdesk/src/renderer/App.tsx, handleActionStart and streaming event listeners -->

1. **ActionToolbar** owns: concurrency guard (rejects clicks when `runningActionId !== null`), command generation via `getCommand`, and calling the parent's `onActionStart` callback
2. **App.tsx** owns: the streaming lifecycle — it calls `window.erkdesk.startStreamingAction()`, listens to `onActionOutput`/`onActionCompleted` IPC events, manages log panel visibility, and clears `runningActionId` on completion

This split matters because the toolbar is a pure rendering component — it doesn't know about IPC, log state, or streaming. The `onActionStart` prop is a fire-and-forget callback. App.tsx subscribes to IPC events in a separate `useEffect` and manages all streaming state.

**Why not blocking?** If `handleClick` awaited action completion, the entire UI would freeze during long-running erk commands (landing, addressing reviews). Streaming lets the LogPanel show real-time output.

## Button State Model

Buttons have three visual states, but the logic collapses to two booleans:

- **Disabled**: no plan selected, OR predicate fails, OR _any_ action is running (global lock)
- **Running**: this specific action is the one currently executing (shows `"Label..."` text)
- **Active**: plan selected, predicate passes, nothing running

The global lock (disabling all buttons while any action runs) prevents concurrent action execution. This is simpler than per-action locking and prevents race conditions in the IPC streaming layer, which supports only one active stream at a time.

## Related Documentation

Related erkdesk documentation in this category covers app architecture, IPC patterns, and development tripwires.
