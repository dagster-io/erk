---
title: Defensive Bounds Handling
read_when:
  - working with WebContentsView bounds in erkdesk
  - debugging Electron crashes related to setBounds
  - adding new IPC handlers that pass coordinates to Electron APIs
tripwires:
  - action: "passing renderer-reported bounds to Electron APIs"
    warning: "never pass renderer-reported bounds directly to Electron setBounds() without clamping"
  - action: "implementing bounds validation in erkdesk"
    warning: "always clamp at the main process trust boundary, not only in the renderer"
---

# Defensive Bounds Handling

Electron's `WebContentsView.setBounds()` silently crashes on fractional or negative values. The erkdesk architecture handles this through a **defense-in-depth split**: the renderer enforces logical constraints, and the main process enforces API-level safety at the trust boundary.

## Why This Exists

`getBoundingClientRect()` can return fractional pixels (CSS transforms, zoom levels) and, in rare browser quirks, negative coordinates. Passing these directly to `setBounds()` causes silent Electron crashes — no error message, just termination. The failure mode varies by platform.

## Defense-in-Depth: Two Layers, Two Responsibilities

| Layer                          | Responsibility      | Enforces                              |
| ------------------------------ | ------------------- | ------------------------------------- |
| **Renderer** (SplitPane)       | Logical correctness | Min widths, divider position clamping |
| **Main process** (IPC handler) | API safety          | Non-negative integers for all bounds  |

**Why not just validate in the renderer?** The main process is the trust boundary — it directly calls Electron APIs and must never assume renderer data is well-formed. Additional sources of bounds may be added in the future, and the main process must be robust against all of them.

<!-- Source: erkdesk/src/main/index.ts, ipcMain.on("webview:update-bounds") -->

See the `webview:update-bounds` handler in `erkdesk/src/main/index.ts` for the clamping implementation. The renderer-side constraint logic is in `SplitPane.tsx`'s drag handler.

## Zero-Bounds Initialization

The WebContentsView starts at zero bounds with `about:blank` because no valid position exists until the renderer measures the split layout. This prevents a flash of incorrectly-positioned content — the view is effectively invisible until the first bounds report arrives via IPC.

## Anti-Patterns

**WRONG**: Passing `getBoundingClientRect()` values directly through IPC to `setBounds()` without clamping. Even though the values are "usually" integers, edge cases (zoom, CSS transforms, mid-resize race conditions) will produce fractional values that crash Electron silently.

**WRONG**: Clamping only in the renderer. The main process must independently ensure safety because it's the trust boundary for Electron API calls.

## Related Documentation

- [WebView API](webview-api.md) — IPC channels and bounds update flow
- [SplitPane Implementation](split-pane-implementation.md) — Renderer-side layout and bounds reporting lifecycle
