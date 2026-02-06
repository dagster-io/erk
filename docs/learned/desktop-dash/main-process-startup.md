---
title: Main Process Startup
read_when:
  - "working on Electron main process code"
  - "understanding erkdesk application lifecycle"
  - "debugging window creation or startup issues"
  - "implementing platform-specific behavior"
last_audited: "2026-02-06 04:16 PT"
audit_result: edited
---

# Main Process Startup

The Electron main process controls application lifecycle and window creation. Erkdesk's main process follows standard Electron patterns with security-first defaults.

## Entry Point

**File**: `erkdesk/src/main/index.ts`

**Responsibilities**:

1. Create browser windows
2. Handle application lifecycle events
3. Load renderer process (HTML/React)
4. Platform-specific behavior (macOS, Windows, Linux)

## Window Creation

See `createWindow()` in `erkdesk/src/main/index.ts` for the complete implementation, which creates the main browser window with security-first web preferences and sets up WebContentsView for embedded web content.

### Security Defaults

**Critical settings in `webPreferences`**:

```typescript
{
  contextIsolation: true,    // Isolate renderer from Node.js context
  nodeIntegration: false,    // No direct Node.js access in renderer
  preload: path.join(__dirname, "preload.js"),  // Safe bridge via preload
}
```

**Why these matter**:

- `contextIsolation: true` — Prevents renderer from accessing Node.js globals
- `nodeIntegration: false` — Prevents `require()` in renderer code
- `preload` script — Only way to expose Node.js APIs to renderer (via context bridge)

**Security principle**: Renderer process treats untrusted content. Never give direct Node.js access.

## Application Lifecycle

### App Ready Event

```typescript
app.on("ready", createWindow);
```

**When**: Electron has finished initialization

**Action**: Create the main window

**Note**: Some APIs (notifications, menus, tray) only work after "ready" event.

### Window Closed Event

```typescript
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
```

**Platform-specific behavior**:

- **Windows/Linux**: Quit when last window closes
- **macOS**: Keep app running (standard macOS behavior)

**Why**: macOS users expect apps to stay in dock even with no windows.

### Activate Event (macOS)

```typescript
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
```

**When**: User clicks dock icon (macOS only)

**Action**: Re-create window if none exist

**Why**: macOS apps typically re-open window on dock click, even after closing.

## Windows Installer Handling

```typescript
if (require("electron-squirrel-startup")) {
  app.quit();
}
```

**Purpose**: Handle Squirrel.Windows installer events

**Behavior**:

- Installer launches app with special flags for shortcuts/uninstall
- App detects installer mode and quits immediately
- Prevents app from running during installation

**Platform**: Windows only (no-op on macOS/Linux)

## Extending Main Process

### Adding IPC Handlers

See existing IPC handlers in `erkdesk/src/main/index.ts` for patterns (e.g., `plans:fetch`, `actions:execute`). Expose via preload script (see [Preload Bridge Patterns](preload-bridge-patterns.md)).

### Adding Menu Bar

Use `Menu.buildFromTemplate()` and `Menu.setApplicationMenu()` after the "ready" event. See Electron documentation for menu API details.

## Related Documentation

- [Preload Bridge Patterns](preload-bridge-patterns.md) - How preload exposes APIs
- [Erkdesk Project Structure](erkdesk-project-structure.md) - Overall architecture
- [Forge Vite Setup](forge-vite-setup.md) - Build configuration
