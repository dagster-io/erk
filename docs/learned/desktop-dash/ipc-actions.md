---
title: erkdesk IPC Action Pattern
last_audited: "2026-02-08"
audit_result: clean
read_when:
  - "adding new IPC handlers to erkdesk"
  - "choosing between streaming and blocking execution"
  - "debugging IPC event flow or memory leaks"
tripwires:
  - action: "adding IPC handler without updating all 4 locations"
    warning: "Every IPC handler requires updates in main/index.ts (handler), main/preload.ts (bridge), types/erkdesk.d.ts (types), and tests. Missing any location breaks type safety or runtime behavior."
    score: 6
  - action: "forgetting to remove IPC handlers on window close"
    warning: "The main window 'closed' handler must call removeHandler/removeAllListeners for every registered handler and kill any active subprocess. See the cleanup block in main/index.ts."
    score: 6
  - action: "forgetting to remove event listeners on renderer unmount"
    warning: "Call removeActionListeners() in useEffect cleanup. Without this, stale listeners accumulate on re-renders and cause memory leaks or double-firing."
    score: 5
  - action: "using blocking execution for long-running actions"
    warning: "Use streaming (startStreamingAction + events) for actions >1s. Blocking execution (executeAction with execFile) freezes the entire UI because Electron's renderer is single-threaded."
    score: 4
---

# erkdesk IPC Action Pattern

erkdesk's Electron IPC layer connects the React renderer to the Node.js main process. The core design decision is having **two execution models** — streaming and blocking — with a strict **four-location contract** for every handler.

## Why Two Execution Models

Electron's renderer is single-threaded. A blocking `ipcMain.handle` call that takes 5 seconds freezes the entire UI for 5 seconds — no scrolling, no keyboard input, no visual feedback. This is why erkdesk splits actions into two patterns:

| Criteria            | Blocking (`executeAction`)        | Streaming (`startStreamingAction`)         |
| ------------------- | --------------------------------- | ------------------------------------------ |
| Duration            | <1 second                         | >1 second                                  |
| Electron API        | `ipcMain.handle` + `execFile`     | `ipcMain.on` + `spawn`                     |
| Return model        | Promise resolves with full result | Events stream incrementally                |
| UI during execution | Frozen                            | Responsive with live output                |
| Use case            | `erk exec dash-data`              | `erk plan submit`, `erk launch pr-address` |

**Key design choice**: Blocking actions resolve errors (not reject) with `success: false`. This gives the renderer a consistent result shape whether the subprocess succeeds or fails, avoiding try/catch branching in every caller.

**Key design choice**: Streaming kills any active subprocess before starting a new one. Only one streaming action runs at a time. This prevents orphaned processes and overlapping output.

## Four-Location Contract

Every IPC handler touches **four files that must stay in sync**. This is the most common source of bugs when adding new handlers — forgetting one location compiles fine but fails at runtime or in tests.

| Location                         | Role                    | Consequence of Missing                           |
| -------------------------------- | ----------------------- | ------------------------------------------------ |
| `erkdesk/src/main/index.ts`      | Handler implementation  | Runtime error: channel has no handler            |
| `erkdesk/src/main/preload.ts`    | Context bridge exposure | Runtime error: `window.erkdesk.foo` is undefined |
| `erkdesk/src/types/erkdesk.d.ts` | TypeScript types        | Type errors in renderer code                     |
| Tests (mock or integration)      | Coverage                | Silent regressions                               |

## Handler Type Decision: `on` vs `handle`

Electron offers two IPC registration patterns, and erkdesk uses them for different purposes:

- **`ipcMain.on`** — fire-and-forget. Used for streaming actions and one-way notifications (WebView bounds updates, URL loads). The renderer doesn't await a return value.
- **`ipcMain.handle`** — request-response. Used for blocking actions where the renderer `await`s a typed result. Maps to `ipcRenderer.invoke` in the preload bridge.

Choosing the wrong one is a subtle bug: using `handle` for streaming means the renderer waits for a Promise that never resolves (the stream has no single return value). Using `on` for blocking means the renderer gets no result back.

## Cleanup: Two Sides, Two Patterns

IPC listeners leak memory if not cleaned up. erkdesk has cleanup on **both sides** of the IPC boundary, for different reasons:

**Main process** (window close): Every `ipcMain.on` and `ipcMain.handle` registered inside `createWindow` must be removed when the window closes. Otherwise, reopening a window (macOS `activate` event) double-registers handlers, causing duplicate responses.

<!-- Source: erkdesk/src/main/index.ts, mainWindow.on('closed') handler -->

See the `mainWindow.on('closed')` handler in `erkdesk/src/main/index.ts` — it removes all five IPC registrations and kills any active subprocess.

**Renderer** (component unmount): The `useEffect` in App.tsx that registers `onActionOutput` and `onActionCompleted` listeners must call `removeActionListeners()` in its cleanup function. Without this, React's strict mode (which double-mounts in development) causes listeners to stack.

<!-- Source: erkdesk/src/renderer/App.tsx, useEffect with removeActionListeners -->

See the `useEffect` cleanup in `erkdesk/src/renderer/App.tsx` that calls `window.erkdesk.removeActionListeners()`.

## ANSI Stripping

Subprocess output from CLI tools contains ANSI escape codes for terminal colors. The main process strips these before forwarding to the renderer because React renders raw text, not terminal escapes. The strip happens on the main process side (not renderer) so the event data is clean by the time it crosses the IPC boundary.

<!-- Source: erkdesk/src/main/index.ts, stripAnsi helper -->

See `stripAnsi` in the streaming handler in `erkdesk/src/main/index.ts`.

## Related Documentation

- [App Architecture](app-architecture.md) — how App.tsx coordinates streaming actions with state
- [Action Toolbar](action-toolbar.md) — action definitions and execution triggers
- [Preload Bridge Patterns](preload-bridge-patterns.md) — contextBridge security model
- [Backend Communication](backend-communication.md) — broader CLI communication patterns
