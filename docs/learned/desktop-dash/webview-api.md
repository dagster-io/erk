---
title: WebView API
read_when:
  - working with WebContentsView in erkdesk, implementing split-pane layout, debugging bounds updates or URL loading
---

# WebView API

The erkdesk desktop application uses Electron's `WebContentsView` to embed web content. The renderer communicates with the main process via IPC channels to control the webview's bounds and loaded URL.

## TypeScript Interface

**File**: `erkdesk/src/types/erkdesk.d.ts`

```typescript
export interface WebViewBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ErkdeskAPI {
  version: string;
  updateWebViewBounds: (bounds: WebViewBounds) => void;
  loadWebViewURL: (url: string) => void;
}

declare global {
  interface Window {
    erkdesk: ErkdeskAPI;
  }
}
```

## IPC Channels

### `webview:update-bounds`

**Purpose**: Update the position and size of the WebContentsView based on renderer measurements.

**Direction**: Renderer → Main process

**Payload**: `WebViewBounds` object with `x`, `y`, `width`, `height` properties.

**Handler** (in `erkdesk/src/main/index.ts:37-45`):

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

**Notes**:

- Bounds are defensively clamped to `Math.max(0, ...)` and floored to prevent fractional/negative coordinates.
- See [Defensive Bounds Handling](defensive-bounds-handling.md) for rationale.

### `webview:load-url`

**Purpose**: Load a URL in the WebContentsView.

**Direction**: Renderer → Main process

**Payload**: String URL.

**Handler** (in `erkdesk/src/main/index.ts:48-53`):

```typescript
ipcMain.on("webview:load-url", (_event, url: string) => {
  if (!webView) return;
  if (typeof url === "string" && url.length > 0) {
    webView.webContents.loadURL(url);
  }
});
```

**Validation**: URL must be a non-empty string.

## Preload Bridge

**File**: `erkdesk/src/main/preload.ts`

The preload script exposes the `erkdesk` API to the renderer via `contextBridge`:

```typescript
contextBridge.exposeInMainWorld("erkdesk", {
  version: "0.1.0",
  updateWebViewBounds: (bounds: WebViewBounds) => {
    ipcRenderer.send("webview:update-bounds", bounds);
  },
  loadWebViewURL: (url: string) => {
    ipcRenderer.send("webview:load-url", url);
  },
});
```

**Usage in renderer**:

```typescript
// Update bounds
window.erkdesk.updateWebViewBounds({
  x: 400,
  y: 0,
  width: 600,
  height: 800,
});

// Load URL
window.erkdesk.loadWebViewURL("http://localhost:3000");
```

## Fire-and-Forget Pattern

**Why `send()` instead of `invoke()`:**

Both `updateWebViewBounds()` and `loadWebViewURL()` use **fire-and-forget** IPC (`ipcRenderer.send()`), not request-response IPC (`ipcRenderer.invoke()`).

**Rationale**:

1. **No return value needed** — The renderer doesn't need confirmation that bounds were updated or URL was loaded.
2. **Frequent updates** — Bounds updates happen on every drag/resize event. Round-trip latency would cause lag.
3. **Main process is authoritative** — The renderer reports what it measured, but the main process decides the final bounds (via defensive clamping).

**Contrast**:

- `send()` = "Here's some data, do something with it" (no response expected)
- `invoke()` = "Here's a request, I need the result" (waits for response)

For WebContentsView bounds updates, `send()` is correct — the renderer is reporting measurements, not requesting state.

## Usage in SplitPane Component

**File**: `erkdesk/src/renderer/components/SplitPane.tsx`

The SplitPane component uses the API to report bounds on:

1. **Initial mount** — Report initial split positions
2. **Divider drag** — Report new bounds as user drags the divider
3. **Window resize** — Report updated bounds when window size changes

**Example**:

```typescript
const reportBounds = (leftWidth: number) => {
  const rightWidth = Math.max(
    MIN_RIGHT_WIDTH,
    containerWidth - leftWidth - DIVIDER_WIDTH,
  );

  window.erkdesk.updateWebViewBounds({
    x: Math.floor(leftWidth + DIVIDER_WIDTH),
    y: 0,
    width: Math.floor(rightWidth),
    height: Math.floor(containerHeight),
  });
};
```

See [SplitPane Implementation](split-pane-implementation.md) for complete lifecycle documentation.

## IPC Cleanup

When the main window closes, IPC listeners are removed to prevent memory leaks:

```typescript
mainWindow.on("closed", () => {
  ipcMain.removeAllListeners("webview:update-bounds");
  ipcMain.removeAllListeners("webview:load-url");
  webView = null;
});
```

**Source**: `erkdesk/src/main/index.ts:70-74`

## Related Documentation

- [SplitPane Implementation](split-pane-implementation.md) — How SplitPane uses this API
- [Defensive Bounds Handling](defensive-bounds-handling.md) — Why bounds are clamped and floored
