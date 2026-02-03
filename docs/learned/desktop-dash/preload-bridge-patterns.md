---
title: Preload Bridge Patterns
read_when:
  - "exposing Node.js APIs to Electron renderer"
  - "implementing IPC communication in erkdesk"
  - "understanding context bridge security"
  - "adding new erkdesk capabilities"
last_audited: "2026-02-03"
audit_result: edited
---

# Preload Bridge Patterns

The preload script is the **only** safe way to expose Node.js APIs to the Electron renderer process.

## The Security Model

- **Constraint**: Renderer has `contextIsolation: true` and `nodeIntegration: false`
- **Result**: Renderer can't access Node.js directly
- **Solution**: Preload script uses `contextBridge` to inject specific APIs into `window.erkdesk`
- **Boundary**: Only explicitly exposed APIs are available to the renderer

## Current Implementation

**Preload**: `erkdesk/src/main/preload.ts`
**Types**: `erkdesk/src/types/erkdesk.d.ts` (full `ErkdeskAPI` interface)

The preload exposes 8 IPC bridge methods on `window.erkdesk`:

- `updateWebViewBounds()`, `loadWebViewURL()` — WebView management
- `fetchPlans()`, `executeAction()` — Request/response IPC
- `startStreamingAction()`, `onActionOutput()`, `onActionCompleted()`, `removeActionListeners()` — Streaming IPC

## Security Anti-Pattern: Never Expose ipcRenderer Directly

```typescript
// WRONG - Security vulnerability!
contextBridge.exposeInMainWorld("erkdesk", {
  ipcRenderer: ipcRenderer, // Exposes entire IPC surface
});
```

**Problem**: Renderer gains unrestricted access to ALL IPC channels. Only expose specific, validated methods.

## Adding a New IPC Method

### Checklist

1. **Add IPC handler** in main process (`erkdesk/src/main/index.ts`):

   ```typescript
   ipcMain.handle("my-channel", async (event, args) => { ... });
   ```

2. **Expose method** in preload (`erkdesk/src/main/preload.ts`):

   ```typescript
   myMethod: (args) => ipcRenderer.invoke("my-channel", args),
   ```

3. **Add TypeScript types** in `erkdesk/src/types/erkdesk.d.ts`:
   - Add method to `ErkdeskAPI` interface
   - Add any new parameter/return types

4. **Call from renderer** via `window.erkdesk.myMethod(args)`

## Security Boundary Mental Model

- **Above**: Main process (full Node.js access, trusted code)
- **At**: Preload script (validates and sanitizes all communication)
- **Below**: Renderer process (sandboxed, treat as untrusted)

**Principle**: Validate all inputs from renderer before acting.

## Related Documentation

- [Main Process Startup](main-process-startup.md) - Where IPC handlers are registered
- [Erkdesk Project Structure](erkdesk-project-structure.md) - Overall architecture
- [Forge Vite Setup](forge-vite-setup.md) - How preload script is built
