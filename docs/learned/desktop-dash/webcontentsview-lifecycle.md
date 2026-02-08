---
audit_result: edited
last_audited: '2026-02-08'
read_when:
- adding or modifying WebContentsView usage in erkdesk
- debugging WebContentsView visibility or positioning issues
- adding new IPC channels in erkdesk's main process
title: WebContentsView Lifecycle
tripwires:
- action: adding a new IPC channel in createWindow
  warning: Every ipcMain.on() or ipcMain.handle() registration MUST have a matching
    removal in the mainWindow.on('closed') handler. on() uses removeAllListeners(channel),
    handle() uses removeHandler(channel). Add both in the same commit.
---

# WebContentsView Lifecycle

Electron's `WebContentsView` is a native OS surface that cannot participate in CSS layout. This creates a three-phase lifecycle that spans three files and two processes — the cross-cutting coordination between them is the main thing an agent can't derive from reading any single file.

## Why Three Phases

Three constraints force this lifecycle:

1. **No valid position at creation time** — the renderer hasn't loaded, so there's nothing to measure
2. **Positions must cross a process boundary** — only the renderer knows DOM layout, but only the main process can call `setBounds()`
3. **Cleanup must live in the main process** — React unmount is unreliable in Electron (see below)

The result: invisible initialization → renderer-driven positioning → main-process-owned cleanup.

## The Three-File Coordination

Each phase involves a different file, and the handoffs between them are the non-obvious part:

| Phase               | File                                            | Role                                                                  |
| ------------------- | ----------------------------------------------- | --------------------------------------------------------------------- |
| 1. Create invisible | `erkdesk/src/main/index.ts`                     | Zero bounds + `about:blank` — prevents flash of mispositioned content |
| 2. Report bounds    | `erkdesk/src/renderer/components/SplitPane.tsx` | Measures placeholder div, sends rect via IPC                          |
| 2. Bridge IPC       | `erkdesk/src/main/preload.ts`                   | Exposes `updateWebViewBounds()` through context bridge                |
| 2. Apply bounds     | `erkdesk/src/main/index.ts`                     | Clamps values and calls `setBounds()` — view becomes visible          |
| 3. Cleanup          | `erkdesk/src/main/index.ts`                     | Removes all IPC listeners, kills processes, nulls references          |

Phase 2 repeats continuously — every drag, resize, or layout change triggers a new bounds report. See [SplitPane Implementation](split-pane-implementation.md) for the four triggers. See [Defensive Bounds Handling](defensive-bounds-handling.md) for why clamping happens at the main process trust boundary.

## Why Cleanup Lives in the Main Process

On macOS, closing the last window doesn't quit the app. The `activate` event calls `createWindow()` again, re-registering all IPC handlers. If the previous window's handlers weren't cleaned up in the `closed` event, the new window's registrations stack on top of leaked ones — causing duplicate handler errors for `handle()` channels and doubled event processing for `on()` channels.

<!-- Source: erkdesk/src/main/index.ts, mainWindow.on("closed") handler and app.on("activate") -->

React's `useEffect` cleanup runs on component unmount, but Electron's window close doesn't guarantee React component lifecycle completes. The main process `closed` handler is the only reliable teardown point.

## IPC Cleanup Symmetry Rule

Every IPC registration in `createWindow` must have a matching removal in the `closed` handler. The removal API differs by registration type:

| Registration       | Removal                               | Why different                              |
| ------------------ | ------------------------------------- | ------------------------------------------ |
| `ipcMain.on()`     | `ipcMain.removeAllListeners(channel)` | Event-based, can have multiple listeners   |
| `ipcMain.handle()` | `ipcMain.removeHandler(channel)`      | Request-response, only one handler allowed |

<!-- Source: erkdesk/src/main/index.ts, createWindow IPC registrations and closed handler -->

**When adding a new IPC channel**: add both the registration and the cleanup in the same commit. Grep the `closed` handler to verify symmetry before submitting.

## Anti-Patterns

```typescript
// WRONG: Setting arbitrary initial bounds
webView.setBounds({ x: 100, y: 100, width: 600, height: 800 });
// These are guesses — window may be any size, causing off-screen content
```

```typescript
// WRONG: Incomplete cleanup — only nulling the reference
mainWindow.on("closed", () => {
  webView = null; // IPC listeners still attached — leaked into next createWindow() call!
});
```

## Related Documentation

- [Defensive Bounds Handling](defensive-bounds-handling.md) — Why clamping happens at the main process trust boundary
- [SplitPane Implementation](split-pane-implementation.md) — Renderer-side measurement triggers and layout coordination
- [WebView API](webview-api.md) — IPC channel catalog and preload bridge
