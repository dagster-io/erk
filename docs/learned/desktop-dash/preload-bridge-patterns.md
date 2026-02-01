---
title: Preload Bridge Patterns
read_when:
  - "exposing Node.js APIs to Electron renderer"
  - "implementing IPC communication in erkdesk"
  - "understanding context bridge security"
  - "adding new erkdesk capabilities"
---

# Preload Bridge Patterns

The preload script is the **only** safe way to expose Node.js APIs to the Electron renderer process. It uses `contextBridge` to create a controlled API surface on `window.erkdesk`.

## The Security Model

**Constraint**: Renderer process has `contextIsolation: true` and `nodeIntegration: false`

**Result**: Renderer can't access Node.js directly (no `require()`, no `fs`, no `process`)

**Solution**: Preload script runs with Node.js access AND can inject APIs into renderer's `window` object

**Boundary**: `contextBridge` is the gatekeeper — only explicitly exposed APIs are available

## Current Implementation

**File**: `erkdesk/src/main/preload.ts`

```typescript
import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("erkdesk", {
  version: "0.1.0",
  // Future IPC methods will go here:
  // - fetchDashData()
  // - executeCommand()
});
```

**What this does**:

1. Creates `window.erkdesk` object in renderer context
2. Exposes only the properties defined in the object literal
3. Currently exposes only a version string (placeholder)

**Renderer access**:

```typescript
// In React components
console.log(window.erkdesk.version); // "0.1.0"
```

## Pattern: Exposing IPC Methods

To add a new capability (e.g., fetching dashboard data):

### Step 1: Add IPC Handler in Main Process

**File**: `src/main/index.ts`

```typescript
import { ipcMain } from "electron";

ipcMain.handle("fetch-dash-data", async () => {
  // Fetch data from erk CLI or filesystem
  const data = await fetchDashboardData();
  return data;
});
```

### Step 2: Expose Method in Preload

**File**: `src/main/preload.ts`

```typescript
import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("erkdesk", {
  version: "0.1.0",
  fetchDashData: () => ipcRenderer.invoke("fetch-dash-data"),
});
```

### Step 3: Call from Renderer

**File**: `src/renderer/App.tsx`

```typescript
const [data, setData] = useState(null);

useEffect(() => {
  window.erkdesk.fetchDashData().then(setData);
}, []);
```

## Why Not Expose ipcRenderer Directly?

**Dangerous pattern** (NEVER do this):

```typescript
// WRONG - Security vulnerability!
contextBridge.exposeInMainWorld("erkdesk", {
  ipcRenderer: ipcRenderer, // Exposes entire IPC surface
});
```

**Problem**: Renderer gains unrestricted access to ALL IPC channels, including ones you didn't intend.

**Attack scenario**:

1. Renderer loads untrusted content (e.g., user-provided HTML)
2. Malicious script calls `window.erkdesk.ipcRenderer.send("delete-files", "/*")`
3. Main process executes the command

**Correct pattern**: Only expose specific, validated methods.

## Current State: No TypeScript Types

**Missing**: TypeScript definitions for `window.erkdesk`

**Workaround**: Use type assertions in renderer:

```typescript
declare global {
  interface Window {
    erkdesk: {
      version: string;
      fetchDashData?: () => Promise<DashData>;
    };
  }
}
```

**Future**: Add `erkdesk.d.ts` type definitions file.

## Pattern: Two-Way Communication

For events from main process to renderer:

### Main Process Sends Event

```typescript
// In main process
mainWindow.webContents.send("dashboard-updated", newData);
```

### Preload Exposes Listener

```typescript
contextBridge.exposeInMainWorld("erkdesk", {
  onDashboardUpdate: (callback) => {
    ipcRenderer.on("dashboard-updated", (event, data) => callback(data));
  },
});
```

### Renderer Subscribes

```typescript
useEffect(() => {
  window.erkdesk.onDashboardUpdate((data) => {
    setDashData(data);
  });
}, []);
```

## Reserved Namespace: window.erkdesk

All erkdesk-specific APIs live under `window.erkdesk`. This:

1. Avoids naming conflicts with other libraries
2. Makes it clear which APIs are erkdesk-specific
3. Groups related functionality

**Future expansion**:

```typescript
window.erkdesk = {
  version: "0.1.0",
  dashboard: {
    fetch: () => Promise<DashData>,
    subscribe: (callback) => void,
  },
  commands: {
    execute: (cmd: string) => Promise<CommandResult>,
  },
  worktrees: {
    list: () => Promise<WorktreeInfo[]>,
    switch: (path: string) => Promise<void>,
  },
};
```

## Security Boundary

The preload script is the **security boundary**:

- **Above the boundary**: Main process (full Node.js access, trusted code)
- **Below the boundary**: Renderer process (sandboxed, potentially untrusted content)
- **At the boundary**: Preload script (validates and sanitizes all communication)

**Principle**: Treat renderer as untrusted. Validate all inputs from renderer before acting.

## Related Documentation

- [Main Process Startup](main-process-startup.md) - Where IPC handlers are registered
- [Erkdesk Project Structure](erkdesk-project-structure.md) - Overall architecture
- [Forge Vite Setup](forge-vite-setup.md) - How preload script is built
