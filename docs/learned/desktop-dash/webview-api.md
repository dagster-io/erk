---
title: WebView API
read_when:
  - working with WebContentsView in erkdesk, implementing split-pane layout, debugging bounds updates or URL loading
last_audited: "2026-02-05 20:38 PT"
audit_result: edited
---

# WebView API

The erkdesk desktop application uses Electron's `WebContentsView` to embed web content. The renderer communicates with the main process via IPC channels to control the webview's bounds and loaded URL.

## TypeScript Interface

The `ErkdeskAPI` interface and related types are defined in `erkdesk/src/types/erkdesk.d.ts`. The API is exposed to the renderer as `window.erkdesk` and includes WebView control methods (`updateWebViewBounds`, `loadWebViewURL`), plan fetching (`fetchPlans`), and action execution (`executeAction`, `startStreamingAction`, and related streaming listeners).

## IPC Channels

### `webview:update-bounds`

**Purpose**: Update the position and size of the WebContentsView based on renderer measurements.

**Direction**: Renderer -> Main process

**Payload**: `WebViewBounds` object with `x`, `y`, `width`, `height` properties.

**Handler**: See `ipcMain.on("webview:update-bounds", ...)` in `erkdesk/src/main/index.ts`.

Bounds are defensively clamped to `Math.max(0, ...)` and floored to prevent fractional/negative coordinates. See [Defensive Bounds Handling](defensive-bounds-handling.md) for rationale.

### `webview:load-url`

**Purpose**: Load a URL in the WebContentsView.

**Direction**: Renderer -> Main process

**Payload**: String URL (validated as non-empty string).

**Handler**: See `ipcMain.on("webview:load-url", ...)` in `erkdesk/src/main/index.ts`.

## Preload Bridge

The preload script in `erkdesk/src/main/preload.ts` exposes the `erkdesk` API to the renderer via `contextBridge.exposeInMainWorld()`. The WebView methods use `ipcRenderer.send()` (fire-and-forget), while plan/action methods use `ipcRenderer.invoke()` (request-response).

## Fire-and-Forget Pattern

**Why `send()` instead of `invoke()`:**

Both `updateWebViewBounds()` and `loadWebViewURL()` use **fire-and-forget** IPC (`ipcRenderer.send()`), not request-response IPC (`ipcRenderer.invoke()`).

**Rationale**:

1. **No return value needed** -- The renderer doesn't need confirmation that bounds were updated or URL was loaded.
2. **Frequent updates** -- Bounds updates happen on every drag/resize event. Round-trip latency would cause lag.
3. **Main process is authoritative** -- The renderer reports what it measured, but the main process decides the final bounds (via defensive clamping).

**Contrast**:

- `send()` = "Here's some data, do something with it" (no response expected)
- `invoke()` = "Here's a request, I need the result" (waits for response)

For WebContentsView bounds updates, `send()` is correct -- the renderer is reporting measurements, not requesting state.

## Usage in SplitPane Component

The `SplitPane` component in `erkdesk/src/renderer/components/SplitPane.tsx` uses the API to report bounds on:

1. **Initial mount and leftWidth changes** -- via a `useEffect` that calls `reportBounds()`
2. **Window resize** -- via a `resize` event listener
3. **Right pane size changes** -- via a `ResizeObserver` on the right pane element

The `reportBounds` callback reads the right pane's `getBoundingClientRect()` and passes the `x`, `y`, `width`, `height` directly to `window.erkdesk.updateWebViewBounds()`.

See [SplitPane Implementation](split-pane-implementation.md) for complete lifecycle documentation.

## IPC Cleanup

When the main window closes, all IPC listeners and handlers are removed to prevent memory leaks. See the `mainWindow.on("closed", ...)` handler in `erkdesk/src/main/index.ts`, which removes listeners for all registered channels and nulls the `webView` reference.

## Related Documentation

- [SplitPane Implementation](split-pane-implementation.md) -- How SplitPane uses this API
- [Defensive Bounds Handling](defensive-bounds-handling.md) -- Why bounds are clamped and floored
