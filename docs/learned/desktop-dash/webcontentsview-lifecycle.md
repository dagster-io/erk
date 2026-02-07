---
title: WebContentsView Lifecycle
read_when:
  - working with WebContentsView in erkdesk, implementing split-pane with embedded webview, setting up IPC for bounds updates
tripwires:
  - action: "creating WebContentsView or setting bounds"
    warning: "Initialize with zero bounds {x: 0, y: 0, width: 0, height: 0}, wait for renderer to report measurements. Always apply defensive clamping: Math.max(0, Math.floor(value)) to prevent fractional/negative coordinates that cause Electron crashes. Clean up IPC listeners on window close."
last_audited: "2026-02-07 18:13 PT"
audit_result: edited
---

# WebContentsView Lifecycle

Proper initialization, bounds management, and cleanup of Electron's `WebContentsView` is critical to prevent crashes and memory leaks.

## Initialization Pattern

The WebContentsView starts with zero bounds (`{x: 0, y: 0, width: 0, height: 0}`) and loads `about:blank`. See `erkdesk/src/main/index.ts:40-42`.

**Why zero bounds**: The view has no valid position until the renderer measures the split layout. Zero bounds make it invisible, preventing a flash of incorrectly-positioned content during startup.

## Bounds Update Pattern

The `webview:update-bounds` IPC handler applies defensive clamping — `Math.max(0, Math.floor(value))` — to all coordinate values before calling `setBounds()`. See `erkdesk/src/main/index.ts:44-53`.

**Why clamping is critical**: Electron crashes silently on fractional or negative bounds. `Math.floor()` converts fractional pixels to integers; `Math.max(0, ...)` prevents negative coordinates.

See [Defensive Bounds Handling](defensive-bounds-handling.md) for details.

## Cleanup Pattern

The `mainWindow.on("closed")` handler removes all IPC listeners and handlers, kills any active child processes, and nulls the `webView` reference. See `erkdesk/src/main/index.ts:190-201`.

**Why cleanup is critical**: IPC listeners persist after window close unless explicitly removed, causing memory leaks across window recreations. Nulling `webView` allows garbage collection.

## Complete Lifecycle

```
1. Window creation
   ↓
2. Create WebContentsView with zero bounds
   ↓
3. Register IPC listeners (update-bounds, load-url, plans:fetch, actions:execute, actions:start-streaming)
   ↓
4. Load renderer (which measures layout and reports bounds)
   ↓
5. Renderer sends first bounds via IPC
   ↓
6. Main process applies defensive clamping and sets bounds
   ↓
7. WebContentsView becomes visible at correct position
   ↓
8. [User interaction: resize, drag divider]
   ↓
9. Renderer reports new bounds → main process updates
   ↓
10. Window close
   ↓
11. Remove all IPC listeners and handlers, kill active processes
   ↓
12. Set webView = null for garbage collection
```

## Common Mistakes

### Mistake 1: Forgetting Defensive Clamping

```typescript
// WRONG: Trusting renderer bounds directly
webView.setBounds(bounds); // Can crash if bounds contain fractional values
```

**Fix**: Always apply `Math.max(0, Math.floor(value))`.

### Mistake 2: Not Initializing with Zero Bounds

```typescript
// WRONG: Setting arbitrary initial bounds
webView.setBounds({ x: 100, y: 100, width: 600, height: 800 });
```

**Problem**: These values are guesses. If the window is smaller, the WebContentsView appears off-screen.

**Fix**: Initialize with zero bounds and wait for renderer to report measurements.

### Mistake 3: Forgetting IPC Cleanup

```typescript
// WRONG: Not cleaning up on window close
mainWindow.on("closed", () => {
  webView = null; // Listeners still attached!
});
```

**Problem**: IPC listeners leak memory across window recreations.

**Fix**: Always call `ipcMain.removeAllListeners()` for each `on` channel and `ipcMain.removeHandler()` for each `handle` channel. Kill any active child processes.

## Related Documentation

- [WebView API](webview-api.md) — IPC channels and preload bridge
- [SplitPane Implementation](split-pane-implementation.md) — How renderer reports bounds
- [Defensive Bounds Handling](defensive-bounds-handling.md) — Why clamping is necessary
