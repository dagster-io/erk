---
audit_result: edited
last_audited: "2026-02-08"
read_when:
  - adding or modifying WebContentsView IPC channels in erkdesk
  - deciding whether a new IPC channel should be fire-and-forget or request-response
  - debugging why the WebContentsView lags behind the divider during drag
title: WebView IPC Design Decisions
tripwires:
  - action:
      WebView IPC channels (bounds, URL) must be fire-and-forget (send/on), never
      request-response (invoke/handle)
    warning: invoke serializes high-frequency updates and causes visible lag
  - action:
      the WebContentsView starts at zero bounds intentionally; do not set initial
      bounds in createWindow
    warning: see defensive-bounds-handling.md
---

# WebView IPC Design Decisions

The erkdesk WebContentsView channels (`webview:update-bounds`, `webview:load-url`) deliberately use fire-and-forget IPC while all other erkdesk channels use request-response or streaming. This doc explains why, and provides the mental model for choosing which style when adding new channels.

## Why Fire-and-Forget for WebView Channels

Three properties distinguish WebView channels from erkdesk's action/plan channels:

1. **No result needed** — the renderer is pushing measurements, not requesting state. There is no meaningful response for "here are the current bounds."
2. **High frequency** — bounds updates fire on every drag event, resize event, and ResizeObserver callback. Round-trip latency from `invoke` would cause visible lag (see anti-pattern below).
3. **Main process is authoritative** — the renderer reports raw `getBoundingClientRect()` values, but the main process applies defensive clamping before calling `setBounds()`. There is no "response" because the renderer's input and the main process's final values intentionally differ.

The general principle: use fire-and-forget for any channel where the renderer is **pushing telemetry** (mouse positions, scroll offsets, focus changes, bounds) rather than **requesting data**.

<!-- Source: erkdesk/src/main/preload.ts, contextBridge.exposeInMainWorld -->

See the bridge methods in `erkdesk/src/main/preload.ts` — the WebView methods return `void` while the action/plan methods return `Promise`, making the IPC style visible at the type level.

## Choosing IPC Style for New Channels

For the general three-style decision framework (fire-and-forget, request-response, streaming), see [Preload Bridge Patterns](preload-bridge-patterns.md). The WebView-specific decision comes down to one question: **does the renderer need a response?**

If the renderer is reporting state to the main process and doesn't care about the outcome, use fire-and-forget. If the renderer is requesting data or needs to know whether an operation succeeded, use request-response or streaming. The main process transforming renderer input (as with bounds clamping) is a strong signal for fire-and-forget — a response would imply the renderer should adjust, but in this architecture the renderer just keeps reporting and the main process handles safety independently.

## Anti-Pattern: Request-Response for Bounds

**WRONG**: Using `invoke`/`handle` for bounds updates. The renderer would `await` each bounds report, blocking subsequent reports until the main process responds. During a fast drag, this serializes what should be parallel fire-and-forget messages, causing the WebContentsView to visibly lag behind the divider. This is the canonical example of why high-frequency telemetry channels must never use request-response IPC.

## Related Documentation

- [Defensive Bounds Handling](defensive-bounds-handling.md) — zero-bounds initialization and why the main process clamps bounds at the trust boundary
- [SplitPane Renderer-Native Coordination](split-pane-implementation.md) — what triggers bounds reports and how the placeholder div pattern works
- [Preload Bridge Patterns](preload-bridge-patterns.md) — the three IPC styles and four-place rule
- [erkdesk IPC Action Pattern](ipc-actions.md) — the request-response and streaming patterns used by non-WebView channels
