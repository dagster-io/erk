---
audit_result: edited
last_audited: "2026-02-08"
read_when:
  - adding new IPC handlers to erkdesk
  - choosing between streaming and blocking execution
  - debugging IPC event flow or memory leaks
title: erkdesk IPC Action Pattern
tripwires:
  - action: adding IPC handler without updating all 4 locations
    score: 6
    warning:
      Every IPC handler requires updates in main/index.ts (handler), main/preload.ts
      (bridge), types/erkdesk.d.ts (types), and tests. Missing any location compiles
      fine but fails at runtime.
  - action: forgetting to remove IPC handlers on window close
    score: 6
    warning:
      The mainWindow 'closed' handler must remove every registered handler and
      kill any active subprocess. Without this, macOS window re-activation double-registers
      handlers.
  - action: forgetting to remove event listeners on renderer unmount
    score: 5
    warning:
      Call removeActionListeners() in useEffect cleanup. React strict mode double-mounts
      in development, stacking listeners and causing double-fires.
  - action: using ipcMain.handle for streaming or ipcMain.on for blocking
    score: 5
    warning:
      handle for streaming = Promise that never resolves. on for blocking = renderer
      gets no result. Match the Electron API to the communication pattern.
  - action: using blocking execution for long-running actions
    score: 4
    warning:
      Use streaming for actions >1s. Blocking execution freezes the entire Electron
      renderer (single-threaded) — no scrolling, no input, no feedback.
---

# erkdesk IPC Action Pattern

erkdesk's Electron IPC layer has two core design decisions that span multiple files: **two execution models** (streaming vs blocking) chosen based on action duration, and a strict **four-location contract** for every handler.

## Why Two Execution Models

Electron's renderer is single-threaded. A blocking `ipcMain.handle` call that takes 5 seconds freezes the entire UI — no scrolling, keyboard input, or visual feedback. This forces a split:

| Criteria            | Blocking                          | Streaming                   |
| ------------------- | --------------------------------- | --------------------------- |
| Duration            | <1 second                         | >1 second                   |
| Electron API        | `ipcMain.handle` + `execFile`     | `ipcMain.on` + `spawn`      |
| Return model        | Promise resolves with full result | Events stream incrementally |
| UI during execution | Frozen                            | Responsive with live output |

**Error contract**: Blocking actions always resolve (never reject) with `success: false` on failure. This gives the renderer a consistent result shape without try/catch branching in every caller.

**Single-action invariant**: Streaming kills any active subprocess before starting a new one. Only one streaming action runs at a time, preventing orphaned processes and overlapping output.

**ANSI boundary**: Subprocess output is stripped of ANSI escape codes on the main-process side before crossing IPC. This keeps the boundary clean — the renderer receives plain text and never needs terminal-aware rendering.

<!-- Source: erkdesk/src/main/index.ts, actions:start-streaming handler -->

See the `actions:start-streaming` handler and `stripAnsi` helper in `erkdesk/src/main/index.ts` for the streaming implementation.

## Four-Location Contract

Every IPC handler touches four files that must stay in sync. This is the most common source of bugs — forgetting one location compiles fine but fails at runtime or silently drops coverage.

| Location                         | Role                    | Consequence of Missing                           |
| -------------------------------- | ----------------------- | ------------------------------------------------ |
| `erkdesk/src/main/index.ts`      | Handler implementation  | Runtime error: channel has no handler            |
| `erkdesk/src/main/preload.ts`    | Context bridge exposure | Runtime error: `window.erkdesk.foo` is undefined |
| `erkdesk/src/types/erkdesk.d.ts` | TypeScript types        | Type errors in renderer code                     |
| Tests (mock or integration)      | Coverage                | Silent regressions                               |

## Handler Type Decision: `on` vs `handle`

Choosing the wrong Electron IPC pattern creates subtle bugs that don't surface at compile time:

- **`ipcMain.on`** — fire-and-forget. The renderer sends and moves on. Used for streaming actions and one-way notifications (bounds updates, URL loads).
- **`ipcMain.handle`** — request-response. The renderer `await`s a typed result via `ipcRenderer.invoke`. Used for blocking actions.

**Why this matters**: `handle` for a streaming action means the renderer awaits a Promise that never resolves (streams have no single return value). `on` for a blocking action means the renderer gets no result back. The mismatch is silent — no type error, no runtime exception, just broken behavior.

## Cleanup: Two Sides, Two Reasons

IPC listeners leak if not cleaned up, but the two sides of the boundary leak for different reasons:

**Main process** (window close): All handlers registered inside `createWindow` must be removed when the window closes. On macOS, closing and reopening a window (via the `activate` event) re-enters `createWindow`, double-registering handlers and causing duplicate responses.

<!-- Source: erkdesk/src/main/index.ts, mainWindow.on('closed') handler -->

See the `mainWindow.on('closed')` handler in `erkdesk/src/main/index.ts` — it removes all five IPC registrations and kills any active subprocess.

**Renderer** (component unmount): The streaming event listeners (`onActionOutput`, `onActionCompleted`) must be cleaned up via `removeActionListeners()` in `useEffect` cleanup. Without this, React strict mode (which double-mounts in development) stacks listeners, causing events to fire twice.

<!-- Source: erkdesk/src/renderer/App.tsx, useEffect with removeActionListeners -->

See the `useEffect` cleanup in `erkdesk/src/renderer/App.tsx` that calls `window.erkdesk.removeActionListeners()`.

## Related Documentation

- [App Architecture](app-architecture.md) — how App.tsx coordinates streaming actions with state
- [Action Toolbar](action-toolbar.md) — action definitions and execution triggers
- [Preload Bridge Patterns](preload-bridge-patterns.md) — contextBridge security model
- [Backend Communication](backend-communication.md) — broader CLI communication patterns
