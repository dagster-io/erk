---
title: erkdesk IPC Action Pattern
last_audited: "2026-02-07 18:30 PT"
audit_result: clean
read_when:
  - "adding new IPC handlers to erkdesk"
  - "implementing streaming or blocking actions"
  - "debugging IPC event flow"
tripwires:
  - action: "adding IPC handler without updating all 4 locations"
    warning: "Every IPC handler requires updates in 4 files: main/index.ts (handler), main/preload.ts (bridge), types/erkdesk.d.ts (types), tests (mock). Missing any location breaks type safety or tests."
    score: 6
  - action: "forgetting to remove IPC handlers on window close"
    warning: "Call removeHandler() and removeAllListeners() in mainWindow.on('closed') handler. See main/index.ts:190-201 for the pattern. Prevents memory leaks and dangling handlers."
    score: 6
  - action: "forgetting to remove event listeners on renderer unmount"
    warning: "Call removeActionListeners() in useEffect cleanup to prevent memory leaks. See App.tsx lines 124-126 for the pattern."
    score: 5
  - action: "using blocking execution for long-running actions"
    warning: "Use streaming (startStreamingAction + events) for actions >1s. Blocking execution (executeAction) freezes the UI."
    score: 4
---

# erkdesk IPC Action Pattern

erkdesk uses Electron IPC to communicate between the renderer (React) and main process (Node.js). There are two execution patterns: **streaming** (for long-running actions) and **blocking** (for quick operations).

## Four-Location Checklist

Every IPC handler requires changes in **4 locations**:

| File                           | Purpose                                     |
| ------------------------------ | ------------------------------------------- |
| `main/index.ts`                | Handler implementation (main process)       |
| `main/preload.ts`              | Context bridge exposure (renderer access)   |
| `types/erkdesk.d.ts`           | TypeScript types for `window.erkdesk` API   |
| `tests/` (mock or integration) | Test coverage (mock for unit, real for e2e) |

**Tripwire**: Forgetting any of these 4 locations breaks type safety, tests, or runtime behavior.

## Streaming vs Blocking Execution

### Streaming Pattern (Preferred for Long Actions)

**Use when**: Action takes >1 second (e.g., `erk plan submit`, `erk launch pr-address`)

**Flow**:

1. Renderer calls `window.erkdesk.startStreamingAction(command, args)`
2. Main process spawns subprocess with `spawn()`
3. Main process sends `action:output` events for stdout/stderr chunks
4. Main process sends `action:completed` event on exit
5. Renderer listens via `onActionOutput` and `onActionCompleted`

**Advantages**:

- UI remains responsive
- Real-time output streaming
- User can see progress

> **Source**: See [`main/index.ts:130-182`](../../../erkdesk/src/main/index.ts)

The handler spawns the subprocess, strips ANSI codes from stdout/stderr chunks, and forwards them as `action:output` events. On process close, it sends `action:completed` with success/error status.

**ANSI Stripping**: Subprocess output contains ANSI escape codes (colors/formatting). The `stripAnsi` helper removes them before sending to renderer to prevent rendering issues.

### Blocking Pattern (for Quick Operations)

**Use when**: Action completes in <1 second (e.g., `erk exec dash-data`)

**Flow**:

1. Renderer awaits `window.erkdesk.executeAction(command, args)`
2. Main process uses `execFile()` and waits for completion
3. Returns `{ success, stdout, stderr, error }` once complete

> **Source**: See [`main/index.ts:96-118`](../../../erkdesk/src/main/index.ts)

The handler wraps `execFile()` in a Promise, resolving with `{ success, stdout, stderr, error }`. Errors resolve (not reject) with `success: false` for consistent result handling.

**Disadvantage**: UI freezes for the entire duration.

## Event Listener Cleanup Pattern

Streaming actions register event listeners that **must be cleaned up** to prevent memory leaks.

> **Source**: See [`App.tsx:108-127`](../../../erkdesk/src/renderer/App.tsx)

The `useEffect` registers `onActionOutput` (appends log lines) and `onActionCompleted` (updates status, clears running action) listeners on mount, and calls `removeActionListeners()` in the cleanup function on unmount.

**Key insight**: `removeActionListeners()` is called in the cleanup function, running on component unmount.

## Handler Registration Patterns

### ipcMain.on (Fire-and-Forget)

Used for streaming actions and one-way notifications:

```tsx
ipcMain.on("actions:start-streaming", (_event, command, args) => {
  // No return value expected
});
```

### ipcMain.handle (Request-Response)

Used for blocking actions that return values:

```tsx
ipcMain.handle("plans:fetch", (): Promise<FetchPlansResult> => {
  return new Promise((resolve) => {
    // ...
    resolve(result);
  });
});
```

## Preload Bridge Pattern

The preload script exposes IPC methods via `contextBridge`:

```tsx
contextBridge.exposeInMainWorld("erkdesk", {
  startStreamingAction: (command: string, args: string[]) => {
    ipcRenderer.send("actions:start-streaming", command, args);
  },
  onActionOutput: (callback: (event: ActionOutputEvent) => void) => {
    ipcRenderer.on("action:output", (_ipcEvent, event) => {
      callback(event);
    });
  },
  removeActionListeners: () => {
    ipcRenderer.removeAllListeners("action:output");
    ipcRenderer.removeAllListeners("action:completed");
  },
});
```

**Security note**: `contextBridge` isolates renderer from full Node.js access. Only explicitly exposed methods are available.

## Type Safety with TypeScript

The `erkdesk.d.ts` file extends the global `Window` interface:

```tsx
export interface ErkdeskAPI {
  startStreamingAction: (command: string, args: string[]) => void;
  onActionOutput: (callback: (event: ActionOutputEvent) => void) => void;
  onActionCompleted: (callback: (event: ActionCompletedEvent) => void) => void;
  removeActionListeners: () => void;
}

declare global {
  interface Window {
    erkdesk: ErkdeskAPI;
  }
}
```

This enables type-checked access to `window.erkdesk` in renderer code.

## Adding a New IPC Handler

### 1. Define the handler in `main/index.ts`

Choose `ipcMain.on` (streaming) or `ipcMain.handle` (blocking):

```tsx
ipcMain.on("my-action:execute", (_event, arg1, arg2) => {
  // Implementation
});
```

### 2. Expose in `main/preload.ts`

```tsx
contextBridge.exposeInMainWorld("erkdesk", {
  // ... existing methods
  myAction: (arg1: string, arg2: number) => {
    ipcRenderer.send("my-action:execute", arg1, arg2);
  },
});
```

### 3. Add types in `types/erkdesk.d.ts`

```tsx
export interface ErkdeskAPI {
  // ... existing methods
  myAction: (arg1: string, arg2: number) => void;
}
```

### 4. Add test coverage

Either mock the IPC in unit tests or add integration test coverage.

## Related Documentation

- [App Architecture](app-architecture.md) — How App.tsx coordinates streaming actions
- [Action Toolbar](action-toolbar.md) — Action definitions and execution triggers
- [erkdesk Tripwires](tripwires.md) — Critical patterns to follow
