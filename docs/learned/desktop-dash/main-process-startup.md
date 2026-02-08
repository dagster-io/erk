---
title: Main Process Startup
read_when:
  - "adding IPC handlers to the main process"
  - "debugging window recreation or listener leak issues on macOS"
  - "choosing between execFile and spawn for a new IPC handler"
tripwires:
  - action: "Register IPC handlers inside createWindow(), not at module scope"
    warning: "Register IPC handlers inside createWindow(), not at module scope — macOS activate re-calls createWindow, causing duplicate listeners"
  - action: "Every new IPC handler needs matching cleanup in mainWindow.on('closed')"
    warning: "Every new IPC handler needs matching cleanup in mainWindow.on(\"closed\") — use removeAllListeners for ipcMain.on, removeHandler for ipcMain.handle"
  - action: "spawning a new streaming process — concurrent subprocess conflicts cause interleaved output"
    warning: "Kill activeAction before spawning a new streaming process — concurrent subprocess conflicts cause interleaved output"
  - action: "WebContentsView starts at zero bounds — renderer must report bounds before it becomes visible"
    warning: "WebContentsView starts at zero bounds — renderer must report bounds before it becomes visible"
  - action: "Use execFile for request/response IPC, spawn for streaming IPC"
    warning: "Use execFile for request/response IPC, spawn for streaming IPC — do not mix the patterns"
last_audited: "2026-02-08"
audit_result: clean
---

# Main Process Startup

<!-- Source: erkdesk/src/main/index.ts, createWindow() -->

This doc covers cross-cutting architectural decisions in the erkdesk main process. For the security model and IPC method checklist, see [Preload Bridge Patterns](preload-bridge-patterns.md).

## Why IPC Handlers Live Inside createWindow

All IPC handlers are registered inside `createWindow()` rather than at module scope. This is deliberate: on macOS, the `activate` event re-calls `createWindow()` when the user clicks the dock icon after closing all windows. If handlers were registered at module scope, they'd either leak (accumulating duplicate listeners) or fail to reference the new window's `webContents`.

By scoping handlers to `createWindow()`, each window gets its own handler set. The `mainWindow.on("closed")` callback removes all handlers and kills active child processes, ensuring no stale references survive window destruction.

**Anti-pattern**: Registering an IPC handler at module scope. It will survive window close on macOS and reference a destroyed `mainWindow`, causing silent failures or crashes on the next `activate` cycle.

### Cleanup Requires Two Different Methods

Electron uses different registration/cleanup APIs depending on the IPC pattern. When adding a new handler, you must use the matching cleanup call:

| Registration     | Cleanup                      | When to Use                                 |
| ---------------- | ---------------------------- | ------------------------------------------- |
| `ipcMain.on`     | `ipcMain.removeAllListeners` | Fire-and-forget messages (renderer to main) |
| `ipcMain.handle` | `ipcMain.removeHandler`      | Request/response (renderer awaits result)   |

Mixing these up (e.g., calling `removeAllListeners` for a handler registered with `handle`) silently fails to clean up.

## execFile vs spawn: Two Subprocess Patterns

<!-- Source: erkdesk/src/main/index.ts, plans:fetch and actions:start-streaming handlers -->

The main process uses two distinct subprocess patterns for CLI integration, chosen based on the communication model:

| Pattern          | IPC Method       | Electron API | Use When                                                           |
| ---------------- | ---------------- | ------------ | ------------------------------------------------------------------ |
| Request/response | `ipcMain.handle` | `execFile`   | Renderer awaits a single result (data fetches, one-shot actions)   |
| Streaming        | `ipcMain.on`     | `spawn`      | Main pushes incremental output to renderer (long-running commands) |

**Why two patterns**: `execFile` buffers all output and returns it at once — simple but unsuitable for long-running commands where the user needs progress. `spawn` streams stdout/stderr chunks to the renderer via `webContents.send()`, enabling real-time output display.

**Concurrent action safety**: The streaming pattern tracks `activeAction` and kills any prior process before starting a new one. This prevents interleaved output from concurrent subprocesses. See `createWindow()` in `erkdesk/src/main/index.ts` for the kill-before-spawn guard.

**Why ANSI stripping happens in main, not renderer**: The spawn handler strips ANSI escape codes before forwarding to the renderer. This keeps the renderer free of terminal-specific concerns — it receives clean text and doesn't need to parse or filter escape sequences. This is a boundary-of-responsibility decision: the main process owns the subprocess interface and normalizes its output.

## WebContentsView Zero-Bounds Initialization

<!-- Source: erkdesk/src/main/index.ts, webView creation and webview:update-bounds handler -->

The WebContentsView (right-pane embedded browser) starts with zero bounds and `about:blank`. It becomes visible only after the renderer measures its container and sends bounds via the `webview:update-bounds` IPC channel.

**Why not set initial bounds in main**: The main process doesn't know the renderer's layout — CSS flex, panel sizes, and resize state are renderer concerns. The renderer is the source of truth for where the WebContentsView should appear. Setting non-zero initial bounds would cause a visible flash of mispositioned content before the renderer corrects it.

## Lifecycle and Platform Behavior

Standard Electron lifecycle with one platform-specific nuance: `window-all-closed` quits the app on Windows/Linux but is a no-op on macOS (standard dock behavior). Combined with the `activate` handler that re-calls `createWindow()`, this means **the full IPC registration/cleanup cycle can run multiple times per app session on macOS**. This is the primary reason the scoped-handler pattern described above is critical.

## Related Documentation

- [Preload Bridge Patterns](preload-bridge-patterns.md) — Security model and checklist for adding new IPC methods
- [Erkdesk Project Structure](erkdesk-project-structure.md) — Three-target build architecture
- [Forge Vite Setup](forge-vite-setup.md) — How Forge globals control dev vs production loading
