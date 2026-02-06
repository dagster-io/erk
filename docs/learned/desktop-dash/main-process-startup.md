---
title: Main Process Startup
read_when:
  - "working on Electron main process code"
  - "understanding erkdesk application lifecycle"
  - "debugging window creation or startup issues"
  - "implementing platform-specific behavior"
last_audited: "2026-02-05 20:38 PT"
audit_result: edited
---

# Main Process Startup

The Electron main process controls application lifecycle and window creation. Erkdesk's main process follows standard Electron patterns with security-first defaults.

## Entry Point

**File**: `erkdesk/src/main/index.ts`

**Responsibilities**:

1. Create browser window and embedded WebContentsView
2. Register all IPC handlers (WebView bounds, URL loading, plan fetching, action execution, streaming actions)
3. Handle application lifecycle events (ready, window-all-closed, activate)
4. Load renderer process with HMR-aware dev/prod switching
5. Clean up IPC listeners and child processes on window close

## Security Defaults

The `BrowserWindow` and `WebContentsView` both use security-first `webPreferences`. See `createWindow()` in `erkdesk/src/main/index.ts` for the actual configuration.

**Why these settings matter**:

- `contextIsolation: true` -- Prevents renderer from accessing Node.js globals
- `nodeIntegration: false` -- Prevents `require()` in renderer code
- `preload` script -- Only way to expose Node.js APIs to renderer (via context bridge)

**Security principle**: Renderer process treats untrusted content. Never give direct Node.js access.

## Application Lifecycle

Standard Electron lifecycle events are registered at the bottom of `erkdesk/src/main/index.ts`:

- **`app.on("ready", createWindow)`** -- Creates main window after Electron initialization. Some APIs (notifications, menus, tray) only work after this event.
- **`app.on("window-all-closed", ...)`** -- Quits on Windows/Linux; stays running on macOS (standard dock behavior).
- **`app.on("activate", ...)`** -- Re-creates window on macOS dock click if none exist.
- **`electron-squirrel-startup`** -- Handles Windows installer events (Squirrel) by quitting immediately during install/uninstall.

## HMR and Forge Globals

The window loads from Vite dev server in development or bundled files in production, controlled by `MAIN_WINDOW_VITE_DEV_SERVER_URL` and `MAIN_WINDOW_VITE_NAME`. DevTools auto-open in development only. See [Forge Vite Setup](forge-vite-setup.md) for how these globals are configured.

## IPC Architecture

The `createWindow()` function registers several IPC handlers inline. For the adding-a-new-IPC-method checklist, see [Preload Bridge Patterns](preload-bridge-patterns.md).

## Related Documentation

- [Preload Bridge Patterns](preload-bridge-patterns.md) - How preload exposes APIs and checklist for new IPC methods
- [Erkdesk Project Structure](erkdesk-project-structure.md) - Overall architecture
- [Forge Vite Setup](forge-vite-setup.md) - Build configuration and Forge globals
