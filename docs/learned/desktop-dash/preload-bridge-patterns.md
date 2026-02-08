---
audit_result: edited
last_audited: "2026-02-08"
read_when:
  - adding new IPC methods to erkdesk
  - debugging communication between renderer and main process
  - writing tests that mock the erkdesk bridge API
  - understanding Electron security boundaries in erkdesk
title: Preload Bridge Patterns
tripwires:
  - action: Never expose ipcRenderer directly
    warning: only wrap individual channels as named methods
  - Every bridge method must appear in four places:
      main handler, preload exposure,
      type interface, and window-close cleanup
    action: performing this action
    warning: Check the relevant documentation.
  - action: Tests mock window.erkdesk, not ipcRenderer
    warning: the bridge is the test boundary
  - Streaming IPC requires a trio of bridge methods:
      start, listen, and cleanup — forgetting
      cleanup causes memory leaks
    action: performing this action
    warning: Check the relevant documentation.
---

# Preload Bridge Patterns

The preload bridge is the cross-cutting seam that connects erkdesk's three process layers: main (trusted Node.js), preload (security boundary), and renderer (sandboxed React). Every IPC feature must be threaded through all three, and mistakes in any layer break the others silently.

## Why Context Isolation Matters

Electron's `contextIsolation: true` + `nodeIntegration: false` means the renderer cannot access Node.js APIs at all. The preload script is the **only** way to bridge this gap, using `contextBridge.exposeInMainWorld()` to inject a controlled API surface onto `window.erkdesk`.

The alternative — exposing `ipcRenderer` directly — is a security vulnerability because it gives the renderer unrestricted access to every IPC channel, including any added in the future. The named-method pattern ensures each capability is explicitly granted.

## Three IPC Styles

Erkdesk uses three distinct IPC patterns. Choosing wrong causes subtle bugs (hanging promises or lost events).

| Pattern              | Electron API                                | Use When                                          | Bridge Method Style                   |
| -------------------- | ------------------------------------------- | ------------------------------------------------- | ------------------------------------- |
| **Fire-and-forget**  | `ipcRenderer.send()` / `ipcMain.on()`       | One-way notifications (bounds updates, URL loads) | Void return                           |
| **Request-response** | `ipcRenderer.invoke()` / `ipcMain.handle()` | Need a result back (fetch data, execute action)   | Returns Promise                       |
| **Streaming**        | `send()` to start + `on()` for events       | Long-running processes with incremental output    | Separate start/listen/cleanup methods |

**Key insight**: Streaming requires a **trio** of bridge methods — one to start, one (or more) to listen, and one to clean up listeners. Forgetting the cleanup method causes memory leaks because `ipcRenderer.on()` listeners accumulate across React re-renders.

<!-- Source: erkdesk/src/main/preload.ts, removeActionListeners -->

See `removeActionListeners()` in `erkdesk/src/main/preload.ts` for the renderer-side listener cleanup pattern.

## The Four-Place Rule

Adding a new IPC method requires synchronized changes in four places. Missing any one produces confusing errors — TypeScript may not catch mismatches across the process boundary since main and renderer are separate compilation targets.

1. **Main process handler** — register with `ipcMain.handle()` or `ipcMain.on()`
2. **Preload exposure** — wrap the channel in a named method on `window.erkdesk`
3. **Type interface** — add the method signature to `ErkdeskAPI`
4. **Window-close cleanup** — deregister in the `mainWindow.on("closed")` handler

<!-- Source: erkdesk/src/main/index.ts, ipcMain handlers -->
<!-- Source: erkdesk/src/main/preload.ts, contextBridge.exposeInMainWorld -->
<!-- Source: erkdesk/src/types/erkdesk.d.ts, ErkdeskAPI interface -->

See the IPC handler registrations in `erkdesk/src/main/index.ts`, the bridge exposure in `erkdesk/src/main/preload.ts`, and the `ErkdeskAPI` interface in `erkdesk/src/types/erkdesk.d.ts`.

### Two Kinds of Cleanup

Erkdesk has cleanup responsibilities on **both sides** of the process boundary, and confusing them causes different bugs:

| Cleanup Side         | Where                                         | Deregisters                                           | Failure Mode                                              |
| -------------------- | --------------------------------------------- | ----------------------------------------------------- | --------------------------------------------------------- |
| **Main process**     | `mainWindow.on("closed")` in `index.ts`       | IPC handlers (`removeHandler` / `removeAllListeners`) | Handler-already-registered errors on window recreation    |
| **Renderer process** | Bridge method (e.g., `removeActionListeners`) | `ipcRenderer.on()` callbacks                          | Memory leaks from accumulated listeners across re-renders |

<!-- Source: erkdesk/src/main/index.ts, mainWindow.on("closed") -->

The main-side cleanup in the `"closed"` handler must use the correct deregistration API: `ipcMain.removeHandler()` for `handle()`-registered channels, `ipcMain.removeAllListeners()` for `on()`-registered channels. Using the wrong one is a silent no-op.

## Testing the Bridge Boundary

Tests mock `window.erkdesk`, not the underlying `ipcRenderer`. This is deliberate — the bridge API is the contract that renderer components depend on, and testing against it validates the actual interface boundary rather than implementation details.

<!-- Source: erkdesk/src/test/setup.ts, mockErkdesk -->

See the `mockErkdesk` object in `erkdesk/src/test/setup.ts` for the global mock setup. Individual tests use `vi.mocked(window.erkdesk.methodName)` to configure per-test behavior.

**Why not mock ipcRenderer?** Because renderer code never imports `ipcRenderer` — it only accesses `window.erkdesk`. Mocking ipcRenderer would test an internal detail the renderer doesn't use, making tests fragile to preload refactoring.

## Anti-Pattern: Exposing ipcRenderer Directly

```typescript
// WRONG - Security vulnerability!
contextBridge.exposeInMainWorld("erkdesk", {
  ipcRenderer: ipcRenderer,
});
```

This grants the renderer unrestricted access to ALL IPC channels — current and future. Any XSS vulnerability in the renderer would escalate to full Node.js access.

## Related Documentation

- [Main Process Startup](main-process-startup.md) — where IPC handlers are registered
- [Erkdesk Project Structure](erkdesk-project-structure.md) — overall architecture
- [Forge Vite Setup](forge-vite-setup.md) — how preload script is built
