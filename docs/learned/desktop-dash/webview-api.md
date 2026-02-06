---
title: WebView API
read_when:
  - working with WebContentsView in erkdesk, implementing split-pane layout, debugging bounds updates or URL loading
last_audited: "2026-02-06 04:18 PT"
audit_result: edited
---

# WebView API

The erkdesk desktop application uses Electron's `WebContentsView` to embed web content. The renderer communicates with the main process via IPC channels to control the webview's bounds and loaded URL.

## TypeScript Interface

See `erkdesk/src/types/erkdesk.d.ts` for the complete `WebViewBounds` and `ErkdeskAPI` interfaces. The API includes webview control methods (`updateWebViewBounds`, `loadWebViewURL`) plus plan fetching and action execution methods.

## IPC Channels

### `webview:update-bounds`

**Purpose**: Update the position and size of the WebContentsView based on renderer measurements.

**Direction**: Renderer → Main process

**Payload**: `WebViewBounds` object with `x`, `y`, `width`, `height` properties.

**Handler**: See `erkdesk/src/main/index.ts` (search for `webview:update-bounds`). Bounds are defensively clamped to `Math.max(0, ...)` and floored to prevent fractional/negative coordinates. See [Defensive Bounds Handling](defensive-bounds-handling.md) for rationale.

### `webview:load-url`

**Purpose**: Load a URL in the WebContentsView.

**Direction**: Renderer → Main process

**Payload**: String URL.

**Handler**: See `erkdesk/src/main/index.ts` (search for `webview:load-url`). Validates that URL is a non-empty string before loading.

## Preload Bridge

See `erkdesk/src/main/preload.ts` for how the `erkdesk` API is exposed to the renderer via `contextBridge.exposeInMainWorld()`. The webview methods use `ipcRenderer.send()` for fire-and-forget communication.

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

See [SplitPane Implementation](split-pane-implementation.md) for complete lifecycle documentation and example usage.

## IPC Cleanup

When the main window closes, IPC listeners are removed to prevent memory leaks. See the `mainWindow.on("closed", ...)` handler in `erkdesk/src/main/index.ts` for the complete cleanup sequence (removes listeners, handlers, kills active processes).

## Related Documentation

- [SplitPane Implementation](split-pane-implementation.md) — How SplitPane uses this API
- [Defensive Bounds Handling](defensive-bounds-handling.md) — Why bounds are clamped and floored
