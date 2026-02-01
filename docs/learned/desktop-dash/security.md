---
title: erkdesk Security Architecture
read_when:
  - "implementing Electron context bridge"
  - "working with erkdesk frontend-backend communication"
  - "handling GitHub tokens in desktop app"
  - "setting up Electron security settings"
tripwires:
  - action: "implementing Electron IPC without context bridge"
    warning: "NEVER expose Node.js APIs directly to renderer. Use context bridge with preload script. Set contextIsolation: true, nodeIntegration: false."
  - action: "handling GitHub tokens in frontend code"
    warning: "GitHub tokens must NEVER reach the renderer process. Keep all GitHub API calls in the Python backend layer."
---

# erkdesk Security Architecture

The erkdesk desktop application uses Electron's security best practices with strict context isolation between the frontend (React) and backend (Python).

## Core Security Principles

1. **Context Isolation**: Renderer process cannot access Node.js APIs
2. **No Node Integration**: `nodeIntegration: false` prevents direct Node.js access
3. **Preload Script**: Only way to expose controlled APIs to renderer
4. **Token Isolation**: GitHub tokens never leave the Python backend

## Electron Security Settings

All BrowserWindow instances must use these settings:

```javascript
const mainWindow = new BrowserWindow({
  webPreferences: {
    contextIsolation: true, // ✅ REQUIRED: Isolate renderer from Node.js
    nodeIntegration: false, // ✅ REQUIRED: No direct Node.js access
    preload: path.join(__dirname, "preload.js"), // Only safe API exposure
  },
});
```

**FORBIDDEN patterns**:

```javascript
// ❌ NEVER DO THIS
nodeIntegration: true;

// ❌ NEVER DO THIS
contextIsolation: false;

// ❌ NEVER DO THIS
webPreferences: {
} // Missing security settings
```

## Context Bridge Pattern

The preload script is the ONLY way to expose APIs to the renderer:

```javascript
// preload.js
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("erkApi", {
  // Expose only specific, controlled APIs
  listPlans: () => ipcRenderer.invoke("list-plans"),
  getProgress: (planId) => ipcRenderer.invoke("get-progress", planId),
});
```

Frontend code can then use:

```typescript
// React component
const plans = await window.erkApi.listPlans();
```

**Key properties**:

- `window.erkApi` is the ONLY frontend API surface
- All methods use IPC to communicate with main process
- Main process forwards to Python backend via HTTP/stdio

## GitHub Token Isolation

**CRITICAL**: GitHub tokens must NEVER reach the renderer process.

### ✅ Correct Architecture

```
┌─────────────┐
│   React     │
│  Renderer   │  No token access
└──────┬──────┘
       │ IPC (no tokens)
       ▼
┌─────────────┐
│  Electron   │
│   Main      │  No token access
└──────┬──────┘
       │ HTTP/stdio
       ▼
┌─────────────┐
│   Python    │
│  Backend    │  ✅ Token lives here only
└─────────────┘
```

All GitHub API calls happen in the Python backend:

- Renderer requests "list PRs" via IPC
- Main process forwards to Python
- Python uses GitHub token to call API
- Python returns data (no token) to main process
- Main process returns data to renderer

### ❌ FORBIDDEN Patterns

```javascript
// ❌ NEVER expose token to renderer
contextBridge.exposeInMainWorld("erkApi", {
  getToken: () => process.env.GITHUB_TOKEN, // SECURITY VIOLATION
});

// ❌ NEVER pass token through IPC
ipcRenderer.invoke("github-api", { token: "...", endpoint: "..." });
```

## Preload Script Restrictions

Preload scripts run in a special context with limited privileges:

**Allowed**:

- `contextBridge.exposeInMainWorld()` to expose APIs
- `ipcRenderer.invoke()` to communicate with main process
- Basic JavaScript/TypeScript logic

**Forbidden**:

- File system access (use IPC to main process)
- Network requests (use IPC to backend)
- Process spawning
- Any privileged Node.js APIs

## Security Checklist

When implementing erkdesk features:

- [ ] All BrowserWindows have `contextIsolation: true`
- [ ] All BrowserWindows have `nodeIntegration: false`
- [ ] Only preload script uses `contextBridge`
- [ ] No GitHub tokens in renderer or main process
- [ ] All GitHub API calls in Python backend
- [ ] IPC messages validated in main process

## Related Documentation

- [Backend Communication](backend-communication.md) - How frontend communicates with Python backend
- [Interaction Model](interaction-model.md) - User interaction patterns
- [Framework Evaluation](framework-evaluation.md) - Why Electron was chosen
