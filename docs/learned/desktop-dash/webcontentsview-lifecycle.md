---
title: WebContentsView Lifecycle
read_when:
  - working with WebContentsView in erkdesk, implementing split-pane with embedded webview, setting up IPC for bounds updates
tripwires:
  - action: "creating WebContentsView or setting bounds"
    warning: "Initialize with zero bounds {x: 0, y: 0, width: 0, height: 0}, wait for renderer to report measurements. Always apply defensive clamping: Math.max(0, Math.floor(value)) to prevent fractional/negative coordinates that cause Electron crashes. Clean up IPC listeners on window close."
---

# WebContentsView Lifecycle

Proper initialization, bounds management, and cleanup of Electron's `WebContentsView` is critical to prevent crashes and memory leaks.

## Initialization Pattern

**File**: `erkdesk/src/main/index.ts:32-34`

```typescript
// Start invisible until renderer reports bounds.
webView.setBounds({ x: 0, y: 0, width: 0, height: 0 });
webView.webContents.loadURL("about:blank");
```

**Why zero bounds**:

- The WebContentsView has no valid position until the renderer measures the split layout
- Zero bounds make it invisible (not displayed)
- Prevents flash of incorrectly-positioned content during startup

## Bounds Update Pattern

**File**: `erkdesk/src/main/index.ts:37-45`

```typescript
ipcMain.on("webview:update-bounds", (_event, bounds: WebViewBounds) => {
  if (!webView) return;
  webView.setBounds({
    x: Math.max(0, Math.floor(bounds.x)),
    y: Math.max(0, Math.floor(bounds.y)),
    width: Math.max(0, Math.floor(bounds.width)),
    height: Math.max(0, Math.floor(bounds.height)),
  });
});
```

**Defensive clamping**:

- `Math.floor()` — Convert fractional pixels to integers
- `Math.max(0, ...)` — Prevent negative coordinates
- **Rationale**: Electron crashes silently on fractional or negative bounds

See [Defensive Bounds Handling](defensive-bounds-handling.md) for details.

## Cleanup Pattern

**File**: `erkdesk/src/main/index.ts:70-74`

```typescript
mainWindow.on("closed", () => {
  ipcMain.removeAllListeners("webview:update-bounds");
  ipcMain.removeAllListeners("webview:load-url");
  webView = null;
});
```

**Why cleanup is critical**:

- IPC listeners persist after window close unless explicitly removed
- Memory leaks if listeners accumulate across window recreations
- Setting `webView = null` allows garbage collection

## Complete Lifecycle

```
1. Window creation
   ↓
2. Create WebContentsView with zero bounds
   ↓
3. Register IPC listeners (update-bounds, load-url)
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
11. Remove all IPC listeners
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

**Fix**: Always call `ipcMain.removeAllListeners()` for each channel.

## Related Documentation

- [WebView API](webview-api.md) — IPC channels and preload bridge
- [SplitPane Implementation](split-pane-implementation.md) — How renderer reports bounds
- [Defensive Bounds Handling](defensive-bounds-handling.md) — Why clamping is necessary
