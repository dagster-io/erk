---
title: Main Process Startup
read_when:
  - "working on Electron main process code"
  - "understanding erkdesk application lifecycle"
  - "debugging window creation or startup issues"
  - "implementing platform-specific behavior"
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

### createWindow() Function

```typescript
const createWindow = (): void => {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Load renderer content (HMR-aware)
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(
      path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`),
    );
  }

  // Open DevTools in development only
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.webContents.openDevTools();
  }
};
```

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

### HMR-Aware Loading

The window loads differently in development vs production:

**Development** (Vite dev server):

```typescript
if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
  mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL); // e.g., http://localhost:5173
}
```

**Production** (bundled files):

```typescript
mainWindow.loadFile(
  path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`),
);
```

**Environment variables**:

- `MAIN_WINDOW_VITE_DEV_SERVER_URL` — Set by Electron Forge in dev mode
- `MAIN_WINDOW_VITE_NAME` — Matches `name` in `forge.config.ts` renderer config

### DevTools Auto-Open

```typescript
if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
  mainWindow.webContents.openDevTools();
}
```

**Behavior**: DevTools open automatically in development, never in production.

**Benefit**: Immediate debugging access during development.

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

## Global Variables from Forge

Electron Forge injects globals during build:

```typescript
// Available in main process
MAIN_WINDOW_VITE_DEV_SERVER_URL: string | undefined;
MAIN_WINDOW_VITE_NAME: string;
```

**Source**: `forge.config.ts` renderer configuration:

```typescript
renderer: [
  {
    name: "main_window", // → MAIN_WINDOW_VITE_NAME
    config: "src/renderer/vite.config.ts",
  },
];
```

**Usage**: Construct paths and detect dev vs prod mode.

## Extending Main Process

### Adding IPC Handlers

To expose Node.js functionality to renderer:

1. **Add handler in main process**:

   ```typescript
   import { ipcMain } from "electron";

   ipcMain.handle("read-file", async (event, filePath) => {
     return fs.readFileSync(filePath, "utf-8");
   });
   ```

2. **Expose via preload** (see [Preload Bridge Patterns](preload-bridge-patterns.md))

3. **Call from renderer**:
   ```typescript
   const content = await window.erkdesk.readFile("/path/to/file");
   ```

### Adding Menu Bar

```typescript
import { Menu } from "electron";

const menu = Menu.buildFromTemplate([
  {
    label: "File",
    submenu: [{ role: "quit" }],
  },
]);

Menu.setApplicationMenu(menu);
```

**When**: After "ready" event

## Related Documentation

- [Preload Bridge Patterns](preload-bridge-patterns.md) - How preload exposes APIs
- [Erkdesk Project Structure](erkdesk-project-structure.md) - Overall architecture
- [Forge Vite Setup](forge-vite-setup.md) - Build configuration
